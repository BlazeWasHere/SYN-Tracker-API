#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Any, List, Dict, Literal, Optional, TypeVar, Union, cast, \
    Callable
from datetime import datetime, timedelta
from collections import defaultdict

from hexbytes import HexBytes
import contextlib
import decimal
import logging

from web3.types import _Hash32, TxReceipt, LogReceipt, TxData
from gevent import Greenlet
from web3.main import Web3
import simplejson as json
from redis import Redis
import dateutil.parser
import redis_lock
import gevent

from .data import REDIS, TOKEN_DECIMALS, SYN_DATA

logger = logging.Logger(__name__)
D = decimal.Decimal
KT = TypeVar('KT')
VT = TypeVar('VT')
T = TypeVar('T')


def add_to_dict(dict: Dict[KT, VT], key: KT, value: VT) -> None:
    """
    Equivalent of `dict[key] += value` without the nuisance 
    of key not existing in dict.
    """
    if key in dict:
        # Let's just let python raise an error here if it isn't supported.
        dict[key] += value  # type: ignore
    else:
        dict.update({key: value})


def merge_many_dicts(dicts: List[Dict[KT, Any]],
                     is_price_dict: bool = False) -> Dict[KT, Any]:
    res: Dict[KT, Any] = {}

    for dict in dicts:
        res.update(merge_dict(res, dict, is_price_dict))

    return res


def merge_dict(dict1: Dict[KT, Any],
               dict2: Dict[KT, Any],
               is_price_dict: bool = False) -> Dict[KT, Any]:
    for k, v in dict1.items():
        if isinstance(v, dict):
            if k in dict2 and isinstance(dict2[k], dict):
                merge_dict(dict1[k], dict2[k], is_price_dict)
        else:
            if k in dict2:
                if is_price_dict:
                    if k in ['adjusted', 'current', 'usd']:
                        dict1[k] += dict2[k]  # type: ignore

                else:
                    dict1[k] = dict2[k]

    for k, v in dict2.items():
        if not k in dict1:
            dict1[k] = v

    return dict1


def flatten_dict(_dict: Dict[Any, Any], _join: str = ':') -> str:
    values = []

    for k, v in _dict.items():
        if isinstance(v, dict):
            values.append(flatten_dict(v))
        else:
            values.append(f'{k}-{v}')

    return _join.join(values)


def raise_if(val: Any, match: Any) -> Any:
    if val == match:
        raise TypeError(val)

    return val


def store_volume_dict_to_redis(chain: str, _dict: Dict[str, Any]) -> None:
    # Only cache from 2 days back.
    # TODO: does this even work?
    date = (datetime.now().today() - timedelta(days=2)).timestamp()
    key = chain + ':{date}:{key}'

    for k, v in _dict['data'].items():
        dt = dateutil.parser.parse(k).timestamp()

        if dt < date:
            REDIS.setnx(key.format(date=k, key=list(v.keys())[0]),
                        json.dumps(v))


def get_all_keys(pattern: str,
                 serialize: bool = False,
                 client: Redis = REDIS,
                 index: Union[List[int], int] = 1,
                 use_max_of_duped_keys: bool = False) -> Dict[str, Any]:
    res = cast(Dict[str, Any], defaultdict(dict))
    assert isinstance(index, (int, list))

    for key in client.keys(pattern):
        ret = client.get(key)

        if serialize:
            if ret is not None:
                ret = json.loads(ret, use_decimal=True)

            if index is not None:
                if type(index) == int:
                    key = key.split(':')[index]
                elif type(index) == list:
                    index = cast(List[int], index)

                    if len(index) == 1:
                        key = key.split(':')[index[0]]
                    else:
                        # [min, max]
                        assert len(index) == 2
                        key = ':'.join(key.split(':')[index[0]:index[1]])

        if use_max_of_duped_keys and key in res and res[key]:
            res[key] = max(res[key], ret)
        else:
            res[key] = ret

    return res


def convert_amount(chain: str, token: str, amount: int) -> D:
    try:
        return handle_decimals(amount, TOKEN_DECIMALS[chain][token.lower()])
    except KeyError:
        logger.warning(f'return amount 0 for token {token} on {chain}')
        return D(0)


def hex_to_int(str_hex: str) -> int:
    """
    Convert 0xdead1234 into integer
    """
    return int(str_hex[2:], 16)


def get_gas_stats_for_tx(chain: str,
                         w3: Web3,
                         txhash: _Hash32,
                         receipt: TxReceipt = None) -> Dict[str, D]:
    if receipt is None:
        receipt = w3.eth.get_transaction_receipt(txhash)

    # Arbitrum has this crazy gas bidding system, this isn't some
    # sort of auction now is it?
    if chain == 'arbitrum':
        paid = receipt['feeStats']['paid']  # type: ignore
        paid_for_gas = 0

        for key in paid:
            paid_for_gas += hex_to_int(paid[key])

        gas_price = D(paid_for_gas) / (D(1e9) * D(receipt['gasUsed']))

        return {
            'gas_paid': handle_decimals(paid_for_gas, 18),
            'gas_price': gas_price
        }

    ret = w3.eth.get_transaction(txhash)

    # Optimism seems to be pricing gas on both L1 and L2,
    # so we aggregate these and use gas_spent on L2 to
    # determine the "gas price", L2 gasUsed numbers are somewhat consistent

    # Turns out, Boba does the same. Who would've thought that
    # L2s are not that different?
    if chain in ['optimism', 'boba']:
        paid_for_gas = receipt['gasUsed'] * ret['gasPrice']  # type: ignore
        paid_for_gas += hex_to_int(receipt['l1Fee'])  # type: ignore
        gas_used = receipt['gasUsed']  # type: ignore
        gas_price = D(paid_for_gas) / (D(1e9) * D(gas_used))

        return {
            'gas_paid': handle_decimals(paid_for_gas, 18),
            'gas_price': gas_price
        }

    gas_price = handle_decimals(ret['gasPrice'], 9)  # type: ignore

    return {
        'gas_paid': handle_decimals(gas_price * receipt['gasUsed'], 9),
        'gas_price': gas_price
    }


def dispatch_get_logs(
    cb: Callable[[str, str, LogReceipt], None],
    topics: List[str] = None,
    key_namespace: str = 'logs',
    address_key: Union[str, Literal[-1]] = 'bridge',
    join_all: bool = True,
) -> Optional[List[Greenlet]]:
    from .wrappa.rpc import get_logs, TOPICS

    jobs: List[Greenlet] = []

    for chain in SYN_DATA:
        start_block = None
        addresses = []

        # Some logic to dispatch different addresses for bridge and swap events.
        if address_key != -1:
            addresses.append([SYN_DATA[chain][cast(str, address_key)], None])
        else:
            _start_blocks = {
                'ethereum': {
                    'nusd': 13033711,
                },
                'avalanche': {
                    'nusd': 6619002,
                    'neth': 7378400,
                },
                'bsc': {
                    'nusd': 12431591,
                },
                'polygon': {
                    'nusd': 21071348,
                },
                'arbitrum': {
                    'nusd': 2876718,
                    'neth': 762758,
                },
                'fantom': {
                    'nusd': 21297076,
                },
                'harmony': {
                    'nusd': 19163634,
                },
                'boba': {
                    'nusd': 16221,
                    'neth': 49329,
                },
                'optimism': {
                    'neth': 30819,
                },
                'aurora': {
                    'nusd': 56441515,
                }
            }

            if 'pool_contract' in SYN_DATA[chain]:
                _start_block = _start_blocks[chain]['nusd']
                addresses.append([SYN_DATA[chain]['pool'], _start_block])

            if 'ethpool_contract' in SYN_DATA[chain]:
                _start_block = _start_blocks[chain]['neth']
                addresses.append([SYN_DATA[chain]['ethpool'], _start_block])

        topics = topics or list(TOPICS)

        for x in addresses:
            address, start_block = x[0], x[1]
            if chain in [
                    'harmony',
                    'bsc',
                    'ethereum',
                    'moonriver',
                    'aurora',
                    'moonbeam',
            ]:
                jobs.append(
                    gevent.spawn(get_logs,
                                 chain,
                                 cb,
                                 address,
                                 max_blocks=1024,
                                 topics=topics,
                                 start_block=start_block,
                                 key_namespace=key_namespace))
            elif chain == 'boba':
                jobs.append(
                    gevent.spawn(get_logs,
                                 chain,
                                 cb,
                                 address,
                                 max_blocks=512,
                                 topics=topics,
                                 start_block=start_block,
                                 key_namespace=key_namespace))
            elif chain == 'polygon':
                jobs.append(
                    gevent.spawn(get_logs,
                                 chain,
                                 cb,
                                 address,
                                 max_blocks=2048,
                                 topics=topics,
                                 start_block=start_block,
                                 key_namespace=key_namespace))
            else:
                jobs.append(
                    gevent.spawn(get_logs,
                                 chain,
                                 cb,
                                 address,
                                 topics=topics,
                                 start_block=start_block,
                                 key_namespace=key_namespace))

    if join_all:
        gevent.joinall(jobs)
    else:
        return jobs


def handle_decimals(num: Union[str, int, float, D],
                    decimals: int,
                    *,
                    precision: int = None) -> D:
    if type(num) != D:
        num = str(num)

    res: D = D(num) / D(10**decimals)

    if precision is not None:
        return res.quantize(D(10)**-precision)

    return res


def is_in_range(value: int, min: int, max: int) -> bool:
    return min <= value <= max


def get_airdrop_value_for_block(ranges: Dict[float, List[Optional[int]]],
                                block: int) -> D:
    def _transform(num: float) -> D:
        return D(str(num))

    for airdrop, _ranges in ranges.items():
        # `_ranges` should have a [0] (start) and a [1] (end)
        assert len(_ranges) == 2, f'expected {_ranges} to have 2 items'

        _min: int
        _max: int

        # Has always been this airdrop value.
        if _ranges[0] is None and _ranges[1] is None:
            return _transform(airdrop)
        elif _ranges[0] is None:
            _min = 0
            _max = cast(int, _ranges[1])

            if is_in_range(block, _min, _max):
                return _transform(airdrop)
        elif _ranges[1] is None:
            _min = _ranges[0]

            if _min <= block:
                return _transform(airdrop)
        else:
            _min, _max = cast(List[int], _ranges)

            if is_in_range(block, _min, _max):
                return _transform(airdrop)

    raise RuntimeError('did not converge', block, ranges)


def convert(value: T) -> Union[T, str, List]:
    if isinstance(value, HexBytes):
        return value.hex()
    elif isinstance(value, list):
        return [convert(item) for item in value]
    else:
        return value


def worker_assert_lock(r: Redis, name: str,
                       id: str) -> Union[Literal[False], redis_lock.Lock]:
    # Okay sometimes there is a race condition, hopefully this prevents it.
    import time, random
    time.sleep(random.randint(1, 5))

    lock = redis_lock.Lock(r, name, id=id)

    if not lock.acquire(blocking=True, timeout=15):
        print(f'worker({id}), failed to acquire lock')
        # This should raise `NotAcquired`.
        with contextlib.suppress(redis_lock.NotAcquired):
            lock.release()

        # Just incase it didn't raise an error.
        return False

    assert lock.locked(), 'lock does not exist'
    assert lock._held, f'lock not held by worker({id})'
    return lock


def parse_tx_in(tx_data: TxData) -> Dict[str, Union[int, str]]:
    """
    Parse transaction input for IN bridge transaction
    :param tx_data: tx_data from eth.get_transaction()
    :return: keys: to, token, amount, fee
    """
    result: Dict[str, Union[int, str]] = {}
    # Skip 0x
    inp = tx_data['input'][2:]  # type: ignore
    inp = inp[8:]  # Skip method hash

    address_to = inp[:64]  # Get 'to'
    result['to'] = '0x' + address_to[-40:]  # last 40 symbols is the address
    inp = inp[64:]  # Skip 'to'

    token = inp[:64]  # Get 'token'
    result['token'] = '0x' + token[-40:]  # last 40 symbols is the address
    inp = inp[64:]  # Skip 'token'

    # In the input for IN tx 'amount' is the amount of tokens bridged
    # (nUSD, nETH, SYN, synFRAX ...)
    result['amount'] = int(inp[:64], 16)  # Get 'amount'
    inp = inp[64:]  # Skip 'amount'

    result['fee'] = int(inp[:64], 16)  # Get 'fee'

    return result


def parse_logs_in(log: LogReceipt) -> Dict[str, Union[int, str, bool]]:
    """
    Parse log event for IN bridge transaction
    :param log: log receipt from eth.get_logs()
    :return: keys: to, token, amount_received, fee, [token_index_to,
    swap_success]
    """
    result: Dict[str, Union[int, str, bool]] = {}
    data = log['data'][2:]  # Skip 0x

    token = data[:64]  # Get 'token'
    result['token'] = '0x' + token[-40:]  # last 40 symbols is the address
    data = data[64:]  # Skip 'token'

    # In the logs for IN tx 'amount' is what the user received
    result['amount_received'] = int(data[:64], 16)  # Get 'amount'
    data = data[64:]  # Skip 'amount'

    result['fee'] = int(data[:64], 16)  # Get 'fee'
    data = data[64:]  # Skip 'fee'

    address_to = log['topics'][1].hex()  # Get 'to'
    result['to'] = '0x' + address_to[-40:]  # last 40 symbols is the address

    from syn.utils.explorer.data import TOPIC_TO_EVENT
    event = TOPIC_TO_EVENT[log['topics'][0].hex()]  # Get event topic

    if event == 'TokenMintAndSwap':
        data = data[64:]  # Skip 'token_index_from'

        result['token_index_to'] = int(data[:64], 16)  # Get 'token_index_to'
        data = data[64:]  # Skip 'token_index_to'

        data = data[64:]  # Skip 'min_dy'
        data = data[64:]  # Skip 'deadline'

        result['swap_success'] = int(data[:64], 16) == 1  # Get 'swap_success'
    elif event == 'TokenWithdrawAndRemove':
        token_index_to = int(data[:64], 16)  # Get 'token_index_to'
        data = data[64:]  # Skip 'token_index_to'

        if token_index_to > 3:
            # Older events have swapTokenAmount at this place
            # If extracted value is >3, this is not an index,
            # but rather an amount of tokens.
            # Real token index is the next argument
            token_index_to = int(data[:64], 16)  # Get real 'token_index_to'
            data = data[64:]  # Skip 'token_index_to'

        result['token_index_to'] = token_index_to

        data = data[64:]  # Skip 'swap_min_amount'
        data = data[64:]  # Skip 'deadline'
        result['swap_success'] = int(data[:64], 16) == 1  # Get 'swap_success'

    return result


def parse_logs_out(log: LogReceipt) -> Dict[str, Union[int, str]]:
    """
    Parse log event for OUT bridge transaction
    :param log: log receipt from eth.get_logs()
    :return: keys: to, chain_id, token, amount, [token_index_to]
    """
    result: Dict[str, Union[int, str]] = {}
    data = log['data'][2:]  # Skip 0x

    result['chain_id'] = int(data[:64], 16)  # Get 'chain_id'
    data = data[64:]  # Skip 'chain_id'

    token = data[:64]  # Get 'token'
    result['token'] = '0x' + token[-40:]  # last 40 symbols is the address
    data = data[64:]  # Skip 'token'

    result['amount'] = int(data[:64], 16)  # Get amount
    data = data[64:]  # Skip 'amount'

    address_to = log['topics'][1].hex()  # Get 'to'
    result['to'] = '0x' + address_to[-40:]  # last 40 symbols is the address

    from syn.utils.explorer.data import TOPIC_TO_EVENT
    event = TOPIC_TO_EVENT[log['topics'][0].hex()]  # Get event topic
    if event.endswith('Swap'):
        # TokenDepositAndSwap or TokenRedeemAndSwap
        # events have identical structure
        data = data[64:]  # Skip 'token_index_from'
        result['token_index_to'] = int(data[:64], 16)  # Get 'token_index_to'
    elif event == 'TokenRedeemAndRemove':
        result['token_index_to'] = int(data[:64], 16)  # Get 'token_index_to'

    return result

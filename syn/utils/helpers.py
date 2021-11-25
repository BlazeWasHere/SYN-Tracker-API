#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Any, List, Dict, Optional, TypeVar, Union, cast, Callable
from datetime import datetime, timedelta
from collections import defaultdict
import decimal
import logging

from web3.types import _Hash32, TxReceipt, LogReceipt
from gevent import Greenlet
from web3.main import Web3
import simplejson as json
from redis import Redis
import dateutil.parser
import gevent

from .data import REDIS, TOKEN_DECIMALS, SYN_DATA

logger = logging.Logger(__name__)
D = decimal.Decimal
KT = TypeVar('KT')
VT = TypeVar('VT')


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
                 index: int = 1) -> Dict[str, Any]:
    res = cast(Dict[str, Any], defaultdict(dict))

    for key in client.keys(pattern):
        ret = client.get(key)

        if serialize:
            if ret is not None:
                ret = json.loads(ret, use_decimal=True)

            if index:
                key = key.split(':')[index]

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
    # so we aggregate these and use gas_spent on L1 to
    # determine the "gas price", as L1 gas >>> L2 gas
    if chain == 'optimism':
        paid_for_gas = receipt['gasUsed'] * ret['gasPrice']
        paid_for_gas += hex_to_int(receipt['l1Fee'])
        gas_used = hex_to_int(receipt['l1GasUsed'])
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


def dispatch_get_logs(cb: Callable[[str, str, LogReceipt], None],
                      join_all: bool = True) -> Optional[List[Greenlet]]:
    from .wrappa.rpc import get_logs

    jobs: List[Greenlet] = []

    for chain in SYN_DATA:
        if chain in [
                'harmony',
                'bsc',
                'ethereum',
                'moonriver',
        ]:
            jobs.append(gevent.spawn(get_logs, chain, cb, max_blocks=1024))
        elif chain == 'boba':
            jobs.append(gevent.spawn(get_logs, chain, cb, max_blocks=512))
        elif chain == 'polygon':
            jobs.append(gevent.spawn(get_logs, chain, cb, max_blocks=2048))
        else:
            jobs.append(gevent.spawn(get_logs, chain, cb))

    if join_all:
        gevent.joinall(jobs)
    else:
        return jobs


def handle_decimals(num: Union[str, int, float, decimal.Decimal],
                    decimals: int,
                    *,
                    precision: int = None) -> decimal.Decimal:
    res: decimal.Decimal = D(num) / D(10**decimals)

    if precision is not None:
        return res.quantize(decimal.Decimal(10)**-precision)

    return res

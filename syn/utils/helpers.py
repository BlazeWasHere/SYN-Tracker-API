#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Any, List, Dict, TypeVar, Union, cast
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import json

from eth_typing.evm import ChecksumAddress
from web3.types import _Hash32, TxReceipt
from web3.main import Web3
from redis import Redis
import dateutil.parser

from .explorer.data import Direction, TOKENS_IN_POOL
from .data import REDIS, TOKEN_DECIMALS

logger = logging.Logger(__name__)
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
                ret = json.loads(ret)

            if index:
                key = key.split(':')[index]

        res[key] = ret

    return res


def get_address_from_data(
    chain: str,
    method: str,
    data: dict,
    direction: Direction,
    lower: bool = True,
) -> Union[str, ChecksumAddress]:
    """Get from/to_token from searching through `data` and `log` depending 
    on the `method`"""

    if direction == Direction.OUT:
        address = data['token']
    elif direction == Direction.IN:
        if method in ['TokenWithdraw', 'TokenMint']:
            address = data['token']
        else:
            address = TOKENS_IN_POOL[chain][data['tokenIndexFrom']]

    return Web3.toChecksumAddress(address) if not lower else address.lower()


def convert_amount(chain: str, token: str, amount: int) -> float:
    try:
        return amount / 10**TOKEN_DECIMALS[chain][token.lower()]
    except KeyError:
        logger.warning(f'return amount 0 for token {token} on {chain}')
        return 0


def get_gas_stats_for_tx(chain: str,
                         w3: Web3,
                         txhash: _Hash32,
                         receipt: TxReceipt = None) -> Dict[str, float]:
    if receipt is None:
        receipt = w3.eth.get_transaction_receipt(txhash)

    # Arbitrum has this crazy gas bidding system, this isn't some
    # sort of auction now is it?
    if chain == 'arbitrum':
        paid = receipt['feeStats']['paid']  # type: ignore
        paid_for_gas = 0

        for key in paid:
            paid_for_gas += int(paid[key][2:], 16)

        gas_price = paid_for_gas / (1e9 * receipt['gasUsed'])

        return {'gas_paid': paid_for_gas / 1e18, 'gas_price': gas_price}

    ret = w3.eth.get_transaction(txhash)
    gas_price = ret['gasPrice'] / 1e9  # type: ignore

    return {
        'gas_paid': gas_price * receipt['gasUsed'] / 1e9,
        'gas_price': gas_price
    }
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Any, List, Dict, TypeVar, cast
from datetime import datetime, timedelta
from collections import defaultdict
import json

import dateutil.parser

from .data import REDIS

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


def get_all_keys(pattern: str, serialize: bool = False) -> Dict[str, Any]:
    res = cast(Dict[str, Any], defaultdict(dict))

    for key in REDIS.keys(pattern):
        ret = REDIS.get(key)

        if serialize:
            if ret is not None:
                ret = json.loads(ret)

            key = key.split(':')[1]

        res[key] = ret

    return res

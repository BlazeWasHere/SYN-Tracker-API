#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Any, Callable, Dict, Literal

import dateutil.parser

from syn.utils.data import MORALIS_APIKEY, TOKEN_DECIMALS
from syn.utils.price import get_price_for_address
from syn.utils.wrappa.moralis import Moralis
from syn.utils.helpers import add_to_dict
from syn.utils.cache import timed_cache

if MORALIS_APIKEY is None:
    raise TypeError('`MORALIS_APIKEY` is not set')

moralis = Moralis(MORALIS_APIKEY)


def _always_true(*args, **kwargs) -> Literal[True]:
    return True


@timed_cache(360, maxsize=50)
def get_chain_volume(
        address: str,
        chain: str,
        filter: Callable[[Dict[str, str]],
                         bool] = _always_true) -> Dict[str, Any]:
    # TODO(blaze): Cache past days volume, after all they dont change.
    data = moralis.erc20_transfers(address, chain)
    res: Dict[str, Any] = {}

    for x in data:
        if filter(x) and x['address'] in TOKEN_DECIMALS[chain]:
            value = int(x['value']) / 10**TOKEN_DECIMALS[chain][x['address']]
            key = str(dateutil.parser.parse(x['block_timestamp']).date())
            price = get_price_for_address(chain, x['address'])

            if key not in res:
                res.update({
                    key: {
                        x['address']: {
                            'volume': value,
                            'usd': price * value,
                        },
                        'total': {
                            'usd': 0,
                            'volume': 0,
                        }
                    }
                })
            elif x['address'] not in res[key]:
                res[key].update(
                    {x['address']: {
                         'volume': value,
                         'usd': price * value,
                     }})
            else:
                # Ditto.
                res[key][x['address']]['volume'] += value
                res[key][x['address']]['usd'] += value * price

    # Create a `total` key for each day.
    for k, v in res.items():
        total: Dict[str, float] = {}
        total_usd: float = 0

        for _v in v.values():
            total_usd += _v['usd']

        res[k]['total'] = {'usd': total_usd}

    total: Dict[str, float] = {}
    total_usd: float = 0

    # Now create a `total` including every day.
    for k, v in res.items():
        total_usd += v['total']['usd']

        for token, _v in v.items():
            if 'volume' in _v:
                add_to_dict(total, token, _v['volume'])

    return {
        'stats': {
            'volume': total,
            'usd': total_usd,
        },
        'data': res
    }

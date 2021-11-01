#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Any, Callable, Dict, Literal, Tuple

import dateutil.parser

from syn.utils.data import MORALIS_APIKEY, SYN_DATA, TOKEN_DECIMALS, \
    COVALENT_APIKEY
from syn.utils.price import get_historic_price_for_address, \
    get_price_for_address, get_historic_price_syn
from syn.utils.wrappa.covalent import Covalent
from syn.utils.wrappa.moralis import Moralis
from syn.utils.helpers import add_to_dict
from syn.utils.cache import timed_cache

if COVALENT_APIKEY is None:
    raise TypeError('`COVALENT_APIKEY` is not set')

covalent = Covalent(COVALENT_APIKEY)

if MORALIS_APIKEY is None:
    raise TypeError('`MORALIS_APIKEY` is not set')

moralis = Moralis(MORALIS_APIKEY)


def _always_true(*args, **kwargs) -> Literal[True]:
    return True


def create_totals(res: Dict[str, Any],
                  chain: str) -> Tuple[Dict[str, float], float, float]:
    # Create a `total` key for each day.
    for v in res.values():
        total_usd: float = 0

        for _v in v.values():
            total_usd += _v['usd']

        v['total'] = {'usd': total_usd}

    total: Dict[str, float] = {}
    total_usd_current: float = 0
    # Total adjusted.
    total_usd: float = 0

    # Now create a `total` including every day.
    for v in res.values():
        total_usd += v['total']['usd']

        for token, _v in v.items():
            if 'volume' in _v:
                add_to_dict(total, token, _v['volume'])

    for k, v in total.items():
        price = get_price_for_address(chain, k)
        total_usd_current += (price * v)

    return total, total_usd, total_usd_current


@timed_cache(360, maxsize=50)
def get_chain_volume_covalent(
        address: str,
        contract_address: str,
        chain: str,
        filter: Callable[[Dict[str, Any]],
                         bool] = _always_true) -> Dict[str, Any]:
    data = covalent.transfers_v2(address, contract_address, chain)
    res: Dict[str, Any] = {}

    for y in data:
        for x in y['items']:
            if filter(x):
                # TODO(blaze): there is normally only 1 transfer involved,
                # but what do we do when there is more?
                for z in x['transfers']:
                    value = z['delta_quote']
                    volume = int(z['delta']) / 10**z['contract_decimals']
                    key = str(
                        dateutil.parser.parse(z['block_signed_at']).date())

                    if value is None:
                        if z['contract_ticker_symbol'] == 'SYN':
                            value = volume * get_historic_price_syn(key)
                        else:
                            value = volume * get_historic_price_for_address(
                                chain, z['contract_address'], key)

                    if key not in res:
                        res.update({
                            key: {
                                z['contract_address']: {},
                                'total': {
                                    'usd': 0,
                                    'volume': 0,
                                }
                            }
                        })

                    add_to_dict(res[key][z['contract_address']], 'volume',
                                volume)
                    add_to_dict(res[key][z['contract_address']], 'usd', value)

    total, total_usd, total_usd_current = create_totals(res, chain)

    return {
        'stats': {
            'volume': total,
            'usd': {
                'adjusted': total_usd,
                'current': total_usd_current,
            },
        },
        'data': res
    }


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

            if x['address'] == SYN_DATA['ethereum' if chain ==
                                        'eth' else chain]['address'].lower():
                price = get_historic_price_syn(key)
            else:
                price = get_historic_price_for_address(chain, x['address'],
                                                       key)

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

    total, total_usd, total_usd_current = create_totals(res, chain)

    return {
        'stats': {
            'volume': total,
            'usd': {
                'adjusted': total_usd,
                'current': total_usd_current,
            },
        },
        'data': res
    }

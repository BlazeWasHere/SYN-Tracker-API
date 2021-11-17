#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from collections import defaultdict
from typing import Any, Callable, Dict, Literal, Tuple

import dateutil.parser

from syn.utils.data import MORALIS_APIKEY, SYN_DATA, TOKEN_DECIMALS, \
    COVALENT_APIKEY, POPULATE_CACHE, LOGS_REDIS_URL
from syn.utils.price import get_historic_price_for_address, \
    get_price_for_address, get_historic_price_syn
from syn.utils.helpers import add_to_dict, get_all_keys, merge_dict
from syn.utils.wrappa.covalent import Covalent
from syn.utils.wrappa.moralis import Moralis
from syn.utils.explorer.data import CHAINS
from syn.utils.cache import timed_cache

covalent = Covalent(COVALENT_APIKEY)

moralis = Moralis(MORALIS_APIKEY)


def _always_true(*args, **kwargs) -> Literal[True]:
    return True


def create_totals(res: Dict[str, Any],
                  chain: str,
                  address: str,
                  nested: bool = True) -> Tuple[float, float, float]:
    # Create a `total` key for each day.
    for v in res.values():
        total_usd: float = 0

        if nested:
            for _v in v.values():
                total_usd += _v['price_usd']
        else:
            total_usd += v['price_usd']

        v['total'] = {'usd': total_usd}

    total_volume: float = 0
    total_usd_current: float = 0
    # Total adjusted.
    total_usd: float = 0

    # Now create a `total` including every day.
    for v in res.values():
        total_usd += v['total']['usd']

        for _v in v.values():
            if nested:
                if 'volume' in _v:
                    total_volume += _v['volume']
            else:
                if type(_v) != dict:
                    total_volume += _v

    price = get_price_for_address(chain, address)
    total_usd_current += (price * total_volume)

    return total_volume, total_usd, total_usd_current


def get_chain_volume(address: str,
                     chain: str,
                     direction: str = '*') -> Dict[str, Any]:
    res = defaultdict(dict)

    if 'IN' in direction:
        ret: Dict[str, Dict[str, float]] = get_all_keys(
            f'{chain}:bridge:*:{address}:{direction}',
            client=LOGS_REDIS_URL,
            index=2,
            serialize=True)

        for k, v in ret.items():
            price = get_historic_price_for_address(chain, address, k)

            res[k] = {
                'volume': v['amount'],
                'price_usd': v['amount'] * price,
                'tx_count': v['txCount'],
            }
    elif 'OUT' in direction:
        ret: Dict[str, Dict[str, float]] = get_all_keys(
            f'{chain}:bridge:*:{address}:{direction}',
            client=LOGS_REDIS_URL,
            serialize=True,
            index=False,
        )

        for k, v in ret.items():
            to_chain = CHAINS[int(k.split(':')[-1])]
            date = k.split(':')[2]

            price = get_historic_price_for_address(chain, address, date)

            res[date][to_chain] = {
                'volume': v['amount'],
                'txCount': v['txCount'],
                'price_usd': v['amount'] * price,
            }
    else:
        raise TypeError(f'{direction!r} is invalid.')

    # In direction 'OUT', we add the `to_chain` key so it adds a level of nesting.
    nested = 'OUT' in direction
    total, total_usd, total_usd_current = create_totals(
        res, chain, address, nested)
    #total, total_usd, total_usd_current = 0, 0, 0

    return {
        'stats': {
            'volume': total,
            'usd': {
                'adjusted': total_usd,
                'current': total_usd_current,
            },
        },
        'data': res,
    }


@timed_cache(360, maxsize=50)
def get_chain_metapool_volume(metapool: str, nusd: str, usdlp: str,
                              chain: str) -> Dict[str, Any]:
    transfers_usdlp = covalent.transfers_v2(metapool, usdlp, chain)
    usdlp_is_to_mp: Dict[str, bool] = {}

    for x in transfers_usdlp:
        for y in x['items']:
            for tx in y['transfers']:
                usdlp_is_to_mp[tx['tx_hash']] = (tx['to_address'] == metapool)

    transfers_nusd = covalent.transfers_v2(metapool, nusd, chain)
    res: Dict[str, Any] = {}

    volume_total = 0

    for x in transfers_nusd:
        for y in x['items']:
            if y['tx_hash'] in usdlp_is_to_mp:
                for tx in y['transfers']:
                    is_nusd_to_mp = (tx['to_address'] == metapool)
                    if is_nusd_to_mp != usdlp_is_to_mp[tx['tx_hash']]:
                        volume = int(tx['delta']) / 10**tx['contract_decimals']
                        key = str(
                            dateutil.parser.parse(
                                tx['block_signed_at']).date())

                        add_to_dict(res, key, volume)
                        volume_total += volume
                        # nUSD = 1
                        # add_to_dict(res[key][tx['contract_address']], 'usd', volume)

    # total, total_usd, total_usd_current = create_totals(res, chain)

    return {'stats': {'volume': volume_total}, 'data': res}

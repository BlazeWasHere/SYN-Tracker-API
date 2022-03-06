#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Any, DefaultDict, Dict, Tuple, Union
from collections import defaultdict
from decimal import Decimal
import copy

from gevent.greenlet import Greenlet
import dateutil.parser
import gevent

from syn.utils.price import CoingeckoIDS, get_historic_price_for_address, \
    get_price_for_address, get_price_coingecko
from syn.utils.helpers import add_to_dict, get_all_keys, raise_if
from syn.utils.data import LOGS_REDIS_URL, SYN_DATA
from syn.utils.explorer.data import CHAINS
from syn.utils.cache import timed_cache


def create_totals(
        res: Dict[str, Any],
        chain: str,
        address: Union[str, CoingeckoIDS, float, int],
        is_out: bool = True,
        key: str = 'volume') -> Tuple[Dict[str, Decimal], float, float]:
    total_volume: DefaultDict[str, Decimal] = defaultdict(Decimal)
    total_usd_current: float = 0
    total_txcount: int = 0
    # Total adjusted.
    total_usd: float = 0

    # Create a `total` key which aggregates all the other stats on other keys.
    for v in res.values():
        # Reset the variables on each iteration.
        _total_volume = defaultdict(Decimal)
        _total_txcount: int = 0
        _total_usd: float = 0

        if is_out:
            for _k, _v in v.items():
                total_volume[_k] += _v[key]
                _total_volume[_k] += _v[key]
                _total_txcount += _v['tx_count']
                _total_usd += _v['price_usd']

            v['total'] = {'usd': _total_usd, 'tx_count': _total_txcount}
        else:
            total_volume[chain] += v[key]
            total_txcount += v['tx_count']
            total_usd += v['price_usd']

    # Now create a `total` including every day.
    if is_out:
        for v in res.values():
            total_usd += v['total']['usd']
            total_txcount += v['total']['tx_count']

    if isinstance(address, CoingeckoIDS):
        price = get_price_coingecko(address)
    elif isinstance(address, (int, float)):
        price = address
    else:
        price = get_price_for_address(chain, address)

    for volume in total_volume.values():
        total_usd_current += (price * Decimal(volume))

    return total_volume, total_usd, total_usd_current


def get_chain_volume_total(direction: str) -> Dict[str, Any]:
    assert direction in ['IN', 'OUT']

    def recursive_defaultdict() -> DefaultDict:
        return defaultdict(recursive_defaultdict)

    res = recursive_defaultdict()
    jobs: Dict[str, Greenlet] = {}

    for chain in SYN_DATA.keys():
        jobs[chain] = gevent.spawn(get_chain_volume, chain, direction)

    gevent.joinall(jobs.values())

    for chain, job in jobs.items():
        assert chain not in res
        ret = raise_if(job.get(), None)['data']

        for data in ret.values():
            for date, _data in data['data'].items():
                add_to_dict(res[date], chain, _data['price_usd'])

    totals: Dict[str, Decimal] = {}

    # Calculate totals for each day.
    for date, data in copy.deepcopy(res).items():
        for chain, v in data.items():
            add_to_dict(res[date], 'total', v)
            add_to_dict(totals, chain, v)

    return {'data': res, 'totals': totals}


def get_chain_tx_count_total(direction: str) -> Dict[str, Dict[str, Decimal]]:
    assert direction in ['IN', 'OUT']

    def recursive_defaultdict() -> DefaultDict:
        return defaultdict(recursive_defaultdict)

    res = recursive_defaultdict()

    if direction == 'OUT':
        direction = 'OUT:*'

    ret = get_all_keys(f'*:bridge:*:{direction}',
                       serialize=True,
                       client=LOGS_REDIS_URL,
                       index=False)

    for k, v in ret.items():
        if direction == 'IN':
            chain, _, date, _, _ = k.split(':')
        else:
            chain, _, date, _, _, _ = k.split(':')

        add_to_dict(res[chain], date, v['txCount'])

    totals: Dict[str, Decimal] = {}

    # Calculate totals for each day.
    for date, data in copy.deepcopy(res).items():
        for chain, v in data.items():
            add_to_dict(res[date], 'total', v)
            add_to_dict(totals, chain, v)

    return {'data': res, 'totals': totals}


def get_chain_volume_for_address(address: str,
                                 chain: str,
                                 direction: str = '*') -> Dict[str, Any]:
    def recursive_defaultdict() -> DefaultDict:
        return defaultdict(recursive_defaultdict)

    assert direction in ['IN', 'OUT:*']

    res = recursive_defaultdict()

    ret: Dict[str, Dict[str, str]] = get_all_keys(
        f'{chain}:bridge:*:{address}:{direction}',
        client=LOGS_REDIS_URL,
        index=2 if direction == 'IN' else False,
        serialize=True,
    )

    for k, v in ret.items():
        if direction == 'IN':
            date = k
        else:
            date = k.split(':')[2]

        price = get_historic_price_for_address(chain, address, date)

        add_to_dict(res[date], 'tx_count', v['txCount'])
        add_to_dict(res[date], 'volume', Decimal(v['amount']))
        add_to_dict(res[date], 'price_usd', Decimal(v['amount']) * price)

    total, total_usd, total_usd_current = create_totals(
        res,
        chain,
        address,
        is_out=False,
    )
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


def get_chain_volume(chain: str, direction: str = '*') -> Dict[str, Any]:
    from syn.routes.api.v1.analytics.volume import symbol_to_address

    assert direction in ['IN', 'OUT']

    if direction == 'OUT':
        direction = 'OUT:*'

    # Get all tokens for the chain which we have stored.
    ret = get_all_keys(f'{chain}:bridge:*:{direction}',
                       serialize=True,
                       client=LOGS_REDIS_URL,
                       index=3)
    tokens = ret.keys()

    jobs: Dict[str, Greenlet] = {}

    for token in tokens:
        jobs[token] = gevent.spawn(get_chain_volume_for_address, token, chain,
                                   direction)

    addresses = list(symbol_to_address[chain].values())
    symbols = list(symbol_to_address[chain].keys())
    res = defaultdict(dict)

    # Create totals including everything.
    volume: Dict[str, Dict[str, Union[float, str]]] = {}
    total_usd_current: int = 0
    total_usd_adj: int = 0

    gevent.joinall(jobs.values())

    for token, job in jobs.items():
        assert token not in res
        res[token] = raise_if(job.get(), None)

    for token, v in res.items():
        total_usd_current += v['stats']['usd']['current']
        total_usd_adj += v['stats']['usd']['adjusted']
        volume[token] = v['stats']['volume']

        if chain == 'avalanche' and token in [
                '0x20a9dc684b4d0407ef8c9a302beaaa18ee15f656',
                '0xddf2e2875f0cd6742afd06fd9df8ab6f105e7ec4'
        ]:
            volume[token].update({'token': 'gmx'})
        else:
            volume[token].update({'token': symbols[addresses.index(token)]})

    return {
        'stats': {
            'volume': volume,
            'usd': {
                'adjusted': total_usd_adj,
                'current': total_usd_current,
            },
        },
        'data': res,
    }

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any, Union, Dict, List

from .wrappa.anyscan import get_daily_token_transfers, \
    get_daily_bridge_events
from .wrappa.synapse import get_bridge_volume, extract_token_map

# random date from the distant future
LAST_DAY = '2069-04-20'


def check_bridge_volume(chain: str,
                        token_name: str,
                        decimals=18,
                        skip_last_day=True):
    if chain == 'ethereum':
        direction = 'out'
        txs_scan = get_daily_token_transfers(chain,
                                             'bridge',
                                             token_name,
                                             where_null='')
    else:
        direction = 'in'
        txs_scan = get_daily_token_transfers(chain, 'bridge', token_name)

    volume_stats = get_bridge_volume(chain, direction, token_name)['data']

    if skip_last_day:
        date_until = list(volume_stats)[-1]
    else:
        date_until = LAST_DAY

    total = {
        'amount_scan': 0,
        'volume_scan': 0,
        'amount_api': 0,
        'volume_api': 0
    }

    for date, daily_stats in txs_scan.items():
        if date == date_until:
            break

        _check_volumes(date,
                       daily_stats,
                       volume_stats,
                       total,
                       decimals=decimals,
                       direction=direction)

    return total


def _check_volumes(date: str, daily_stats: Dict[str, int],
                   volume_stats: Dict[str, Any], total: Dict[str, int],
                   decimals: int, direction: str):
    _amount = 0
    _volume = 0

    amount_scan = daily_stats['amount']
    volume_scan = daily_stats['volume']

    if date in volume_stats:
        data = volume_stats[date]
        if direction == 'in':
            _amount = data['tx_count']
            _volume = data['volume'] * 10**decimals
        else:
            for chain, _stats in data.items():
                if chain != 'total':
                    _amount += _stats['tx_count']
                    _volume += _stats['volume']

            _volume *= 10**decimals

    if _amount != amount_scan or _volume != volume_scan:
        get_checked_line(date, [amount_scan, volume_scan, _amount, _volume],
                         decimals)

        total['amount_scan'] += amount_scan - _amount
        total['volume_scan'] += volume_scan - _volume
        total['amount_api'] += _amount - amount_scan
        total['volume_api'] += _volume - volume_scan


def get_checked_line(date: str,
                     data: List[int],
                     decimals: int = 18) -> List[Union[str, int]]:
    return [
        date,
        data[0],
        f'{data[1] / 10 ** decimals:.6f}',
        data[2],
        f'{data[3] / 10 ** decimals:.6f}',
    ]


def check_bridge_events(chain: str, skip_last_day=True):
    data = get_daily_bridge_events(chain)
    total_api_stats = get_bridge_volume(chain, 'out')
    token_map = extract_token_map(total_api_stats)
    total_api_stats = total_api_stats['data']

    for token, token_volume in data.items():
        if token not in total_api_stats:
            print(f'Missing token: {token}')
            continue

        token_name = token_map[token]
        total = {
            'amount_scan': 0,
            'volume_scan': 0,
            'amount_api': 0,
            'volume_api': 0
        }

        volume_stats = total_api_stats[token]['data']
        if skip_last_day:
            date_until = list(token_volume)[-1]
        else:
            date_until = LAST_DAY

        for date, daily_stats in token_volume.items():
            if date == date_until:
                break

            _check_volumes(date,
                           daily_stats,
                           volume_stats,
                           total,
                           decimals=18,
                           direction='out')

        return total

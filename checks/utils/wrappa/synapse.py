#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any, Dict, List

import requests

from utils.helpers import get_json_timeout, print_over
from data import CHAINS, SYMBOLS

API_URL = 'https://synapse.dorime.org/api/v1'


def get_bridge_fees(chain: str, token: str) -> Dict[str, Any]:
    return fetch_data(f'analytics/fees/bridge/{chain}/{token}')


def get_bridge_volume(chain: str,
                      direction: str,
                      token_name='',
                      print_progress=True) -> Dict[str, Any]:
    if token_name == '':
        return fetch_data(f'analytics/volume/{chain}/{direction}',
                          print_progress=print_progress)
    else:
        return fetch_data(
            f'analytics/volume/{chain}/filter/{token_name}/{direction}',
            print_progress=print_progress)


def get_bridge_volume_total(chain: str) -> Dict[str, Dict[str, Any]]:
    return {
        'in': get_bridge_volume(chain, 'in'),
        'out': get_bridge_volume(chain, 'out'),
    }


def get_validator_gas_fees(chain: str, token: str = '') -> Dict[str, Any]:
    if token == '':
        return fetch_data(f'analytics/fees/validator/{chain}')
    else:
        return fetch_data(f'analytics/fees/validator/{chain}/{token}')


def get_chain_airdrop(chain: str,
                      token: str = '') -> Dict[str, Dict[str, Any]]:
    if token == '':
        return fetch_data(f'analytics/fees/airdrop/{chain}')
    else:
        return fetch_data(f'analytics/fees/airdrop/{chain}/{token}')


def fetch_data(request: str, print_progress=True) -> Dict[str, Any]:
    if print_progress:
        print_over(f'Fetching: {request}')
        # print(f'Fetching: {request}')
    url = f'{API_URL}/{request}'
    result = get_json_timeout(requests.get, url)
    if print_progress:
        print_over()
    return result


def get_chain_token_map(chain: str, print_progress=True) -> Dict[str, str]:
    volume = get_bridge_volume(chain, 'in', print_progress=print_progress)
    return extract_token_map(volume)


def extract_token_map(volume: Dict[str, Any]) -> Dict[str, str]:
    token_map = dict()
    for token, stats in volume['stats']['volume'].items():
        token_map[token] = stats['token']

    return token_map


def get_chain_tokens(chain: str) -> List[str]:
    return list(get_chain_token_map(chain).values())


def get_chain_symbols(chain: str) -> List[str]:
    volume = get_bridge_volume(chain, 'in')
    symbols = []
    for stats in volume['stats']['volume'].values():
        if stats['token'] in SYMBOLS:
            symbols.append(SYMBOLS[stats['token']])

    return symbols


def get_all_symbols() -> List[str]:
    result = []
    for chain in CHAINS:
        for symbol in get_chain_symbols(chain):
            if symbol not in result:
                result.append(symbol)

    return result


def get_block_date(chain: str, date: str, print_progress=True) -> int:
    return fetch_data(f'utils/date2block/{chain}/{date}',
                      print_progress=print_progress)[date]['block']

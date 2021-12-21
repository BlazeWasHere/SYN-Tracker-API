#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Dict

import requests

from data import CHAINS, BLOCK_START, TOKENS, EVENTS_OUT
from utils.helpers import get_json_timeout, get_date_from_ts, add_to_dict, \
    hex_to_int, print_over
from utils.wrappa.rpc import get_last_block

URL = {
    'ethereum': 'https://api.etherscan.io',
    'fantom': 'https://api.ftmscan.com',
    'arbitrum': 'https://api.arbiscan.io',
    'polygon': 'https://api.polygonscan.com',
    'avalanche': 'https://api.snowtrace.io/',
    'bsc': 'https://api.bscscan.com',
}

MAX_BLOCKS = 10000
TIMEOUT = 2
NULL_ADDRESS = '0x0000000000000000000000000000000000000000'


def get_daily_token_transfers(chain: str,
                              address_label: str,
                              token_name: str,
                              where_addr='to',
                              where_null='from') -> Dict[str, Dict[str, int]]:
    assert 'scan_key' in CHAINS[chain]
    assert address_label in CHAINS[chain]
    assert token_name in TOKENS[chain]

    url = f'{URL[chain]}/api'

    address = CHAINS[chain][address_label].lower()
    token = TOKENS[chain][token_name]
    block_from = block_start = BLOCK_START[chain][address_label]
    block_till = get_last_block(chain)

    params = {
        'module': 'account',
        'action': 'tokentx',
        'address': address,
        'contractaddress': token,
        'sort': 'asc',
        'apikey': CHAINS[chain]['scan_key'],
    }

    result = dict()

    total_found = 0

    print(f'{chain} from {block_start} to {block_till}')

    while block_from <= block_till:
        block_to = min(block_from + MAX_BLOCKS - 1, block_till)
        params['startblock'] = block_from
        params['endblock'] = block_to

        data = get_json_timeout(requests.get,
                                url=url,
                                params=params,
                                timeout=TIMEOUT)

        if data['result']:
            assert len(data['result']) < 10000
            if data['result'] == 'Invalid API Key':
                raise TypeError('invalid api key for', chain)

            for tx in data['result']:
                if tx[where_addr] == address:
                    if where_null == '' or tx[where_null] == NULL_ADDRESS:
                        add_to_dict(result, {
                            'volume': int(tx['value']),
                            'amount': 1
                        }, get_date_from_ts(tx['timeStamp']))
                        total_found += 1

        percent = 100 * (block_to - block_start) / (block_till - block_start)
        print(f'{chain}: {percent:.1f}% done, found: {total_found}')
        # time.sleep(0.2)
        block_from = block_to + 1

    return result


def get_daily_bridge_events(chain: str) -> \
        Dict[str,
             Dict[str,
                  Dict[str, int]]]:
    """
    :return: {
        "0x123...": {
            "2021-12-01": {
                "volume": 420,
                "amount": 69
            }
        },
        "0xabc...": {
            ...
        }
    }
    """
    assert 'bridge' in CHAINS[chain]
    assert 'scan_key' in CHAINS[chain]
    address = CHAINS[chain]['bridge']

    params = {
        'module': 'logs',
        'action': 'getLogs',
        'address': address,
        'apikey': CHAINS[chain]['scan_key'],
    }

    url = f'{URL[chain]}/api'

    block_from = block_start = BLOCK_START[chain]['bridge']
    block_till = get_last_block(chain)

    result = dict()
    total_found = 0

    while block_from <= block_till:
        block_to = min(block_from + MAX_BLOCKS - 1, block_till)
        params['fromBlock'] = block_from
        params['toBlock'] = block_to

        percent = 100 * (block_to - block_start) / (block_till - block_start)

        topics_done = 0

        for topic in EVENTS_OUT:
            params['topic0'] = topic

            data = get_json_timeout(requests.get,
                                    url=url,
                                    params=params,
                                    timeout=TIMEOUT)

            if data['result']:
                # print(params)
                assert len(data['result']) < 1000

                for log in data['result']:
                    ts = hex_to_int(log['timeStamp'])
                    date = get_date_from_ts(ts)

                    log_hex = log['data'][2:]  # Skip 0x
                    log_hex = log_hex[64:]  # Skip chainId
                    token = log_hex[:64]  # Get token contract
                    token = '0x' + token[
                        -40:]  # last 40 symbols is the address
                    log_hex = log_hex[64:]  # Skip token contract
                    volume = int(log_hex[:64], 16)  # Get amount

                    if token not in result:
                        result[token] = dict()

                    total_found += 1
                    add_to_dict(result[token], {
                        'volume': volume,
                        'amount': 1,
                    }, date)

            topics_done += 1
            print_over(f'{chain}: {percent:.1f}% blocks done, '
                       f'topic {topics_done} out of {len(EVENTS_OUT)}, '
                       f'found: {total_found}')

        block_from = block_to + 1

    print_over()

    return result

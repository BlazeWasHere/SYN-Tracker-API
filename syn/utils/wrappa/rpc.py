#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Any, Dict, List, TypeVar, Union
import json

from web3.types import FilterParams, LogReceipt
from hexbytes import HexBytes
from web3 import Web3

from syn.utils.explorer.poll import handle_event, AttributeDict, Direction
from syn.utils.data import SYN_DATA, LOGS_REDIS_URL
from syn.utils.cache import redis_cache

start_blocks = {
    'ethereum': 13033669,
    'arbitrum': 657404,
    'avalanche': 3376709,
    'bsc': 10065475,
    'fantom': 18503502,
    'polygon': 18026806,
    'harmony': 18646320,
    'boba': 16188,
}

MAX_BLOCKS = 5000
T = TypeVar('T')


def convert(value: T) -> Union[T, str, List]:
    if isinstance(value, HexBytes):
        return value.hex()
    elif isinstance(value, list):
        return [convert(item) for item in value]
    else:
        return value


def _store_if_not_exists(chain: str, address: str, block: int, tx_index: int,
                         data: Dict[str, Any]):
    # Sort of a 'manual' redis cache thing instead of using `redis_cache`.
    key = f'{chain}:logs:{address}:{block}-{tx_index}'
    value = json.dumps({
        'transactionHash': data['transactionHash'],
        'topics': data['topics']
    })

    if LOGS_REDIS_URL.setnx(key, value):
        LOGS_REDIS_URL.set(f'{chain}:logs:{address}:MAX_BLOCK_STORED', block)


def get_logs(chain: str,
             start_block: int = None,
             till_block: int = None,
             max_blocks: int = MAX_BLOCKS) -> None:
    address = SYN_DATA[chain]['bridge']
    w3: Web3 = SYN_DATA[chain]['w3']

    if start_block is None:
        _key = f'{chain}:logs:{address}:MAX_BLOCK_STORED'

        if (ret := LOGS_REDIS_URL.get(_key)) is not None:
            start_block = max(int(ret), start_blocks[chain])
        else:
            start_block = start_blocks[chain]

    if till_block is None:
        till_block = w3.eth.block_number

    import time
    print(
        f'[{chain}] starting from {start_block} with block height of {till_block}'
    )
    _start = time.time()
    x = _start

    while start_block < till_block:
        to_block = min(start_block + max_blocks, till_block)

        params: FilterParams = {
            'fromBlock': start_block,
            'toBlock': to_block,
            'address': w3.toChecksumAddress(address)
        }

        for log in w3.eth.get_logs(params):
            data = {k: convert(v) for k, v in log.items()}
            _store_if_not_exists(chain, address, log['blockNumber'],
                                 log['transactionIndex'], data)

        start_block += max_blocks
        y = round(time.time() - _start, 2)
        print(
            f'[{chain}] elapsed {y}s ({round(y - x, 2)}s) so far at block {start_block}'
        )
        x = y

    print(f'[{chain}] it took {round(time.time() - _start, 2)}s!')
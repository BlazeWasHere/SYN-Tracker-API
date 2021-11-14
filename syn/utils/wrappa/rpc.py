#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import List, TypeVar, Union
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


def _store_if_not_exists(chain: str, address: str, block: int,
                         data: LogReceipt):
    w3: Web3 = SYN_DATA[chain]['w3']

    # Sort of a 'manual' redis cache thing instead of using `redis_cache`.
    key = f'{chain}:logs:{address}:{block}'

    #def cb(event: AttributeDict, _chain: str, data: AttributeDict,
    #          method: str, direction: Direction, logs: AttributeDict) -> None:


def get_logs(chain: str):
    address = SYN_DATA[chain]['bridge']
    start_block = start_blocks[chain]
    w3: Web3 = SYN_DATA[chain]['w3']

    max = w3.eth.block_number

    while start_block < max:
        params: FilterParams = {
            'fromBlock': start_block,
            'toBlock': start_block + MAX_BLOCKS,
            'address': address
        }

        for log in w3.eth.get_logs(params):
            data = {k: convert(v) for k, v in log.items()}
            _store_if_not_exists(chain, address, start_block, log)
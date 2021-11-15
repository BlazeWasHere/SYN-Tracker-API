#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Any, Callable, Dict, List, TypeVar, Union
from datetime import datetime
import json

from web3.types import FilterParams, LogReceipt
from hexbytes import HexBytes
from gevent.pool import Pool
from web3 import Web3
import gevent

from syn.utils.helpers import convert_amount, get_address_from_log_data, \
    get_gas_paid_for_tx
from syn.utils.data import BRIDGE_ABI, OLDBRIDGE_ABI, SYN_DATA, LOGS_REDIS_URL, \
    OLDERBRIDGE_ABI
from syn.utils.explorer.poll import figure_out_method
from syn.utils.explorer.data import TOPICS, Direction

start_blocks = {
    'ethereum': 13136427,
    'arbitrum': 657404,
    'avalanche': 3376709,
    'bsc': 10065475,
    'fantom': 18503502,
    'polygon': 18026806,
    'harmony': 18646320,
    'boba': 16188,
}

pool = Pool(size=64)
MAX_BLOCKS = 5000
T = TypeVar('T')


def convert(value: T) -> Union[T, str, List]:
    if isinstance(value, HexBytes):
        return value.hex()
    elif isinstance(value, list):
        return [convert(item) for item in value]
    else:
        return value


def bridge_callback(chain: str,
                    address: str,
                    log: LogReceipt,
                    abi: str = BRIDGE_ABI) -> None:
    w3: Web3 = SYN_DATA[chain]['w3']
    contract = w3.eth.contract(w3.toChecksumAddress(address), abi=abi)

    receipt = w3.eth.wait_for_transaction_receipt(log['transactionHash'],
                                                  timeout=60)

    ret = figure_out_method(contract, receipt)
    if ret is None:
        if abi == OLDERBRIDGE_ABI:
            raise TypeError(receipt, chain)
        elif abi == OLDBRIDGE_ABI:
            abi = OLDERBRIDGE_ABI
        elif abi == BRIDGE_ABI:
            abi = OLDBRIDGE_ABI
        else:
            raise RuntimeError(f'sanity check? got invalid abi: {abi}')

        return bridge_callback(chain, address, log, abi)

    data, direction, method = ret
    data = data[0]['args']  # type: ignore

    asset = get_address_from_log_data(chain, method, receipt['logs'][0], data,
                                      direction)
    date = w3.eth.get_block(log['blockNumber'])['timestamp']  # type: ignore
    date = datetime.utcfromtimestamp(date).date()

    if (_chain := data.get('chainId')) is not None:
        _chain = f':{_chain}'
    else:
        _chain = ''

    key = f'{chain}:bridge:{date}:{asset}:{direction}{_chain}'

    if direction == Direction.OUT:
        value = {
            'amount': data['amount'] / 10**18,  # This is in nUSD/nETH
            'txCount': 1,
        }
    elif direction == Direction.IN:
        # All `IN` txs are from the validator; let's track how much gas they pay.
        gas = get_gas_paid_for_tx(chain, w3, log['transactionHash'])

        value = {
            'amount': convert_amount(chain, asset, data['amount']),
            'fees': data['fee'] / 10**18,  # This is in nUSD/nETH
            'txCount': 1,
            'validatorGas': gas,
        }
    else:
        raise RuntimeError(f'sanity check? got {direction}')

    if (ret := LOGS_REDIS_URL.get(key)) is not None:
        ret = json.loads(ret)

        if direction == Direction.IN:
            ret['validatorGas'] += value['validatorGas']
            ret['fees'] += value['amount']

        ret['amount'] += value['amount']
        ret['txCount'] += 1

        LOGS_REDIS_URL.set(key, json.dumps(ret))
    else:
        LOGS_REDIS_URL.set(key, json.dumps(value))

    # TODO: What if another thread saves later but is actually behind us?
    LOGS_REDIS_URL.set(f'{chain}:logs:{address}:MAX_BLOCK_STORED',
                       log['blockNumber'])


def get_logs(
    chain: str,
    callback: Callable[[str, str, LogReceipt], None],
    start_block: int = None,
    till_block: int = None,
    max_blocks: int = MAX_BLOCKS,
) -> None:
    address = SYN_DATA[chain]['bridge']
    w3: Web3 = SYN_DATA[chain]['w3']

    if start_block is None:
        _key = f'{chain}:logs:{address}:MAX_BLOCK_STORED'

        if (ret := LOGS_REDIS_URL.get(_key)) is not None:
            start_block = max(int(ret), start_blocks[chain])
        else:
            start_block = start_blocks[chain] + 1

    if till_block is None:
        till_block = w3.eth.block_number

    import time
    print(
        f'[{chain}] starting from {start_block} with block height of {till_block}'
    )
    jobs: List[gevent.Greenlet] = []
    _start = time.time()
    x = _start

    while start_block < till_block:
        to_block = min(start_block + max_blocks, till_block)

        params: FilterParams = {
            'fromBlock': start_block,
            'toBlock': to_block,
            'address': w3.toChecksumAddress(address),
            'topics': [list(TOPICS)],  # type: ignore
        }

        for log in w3.eth.get_logs(params):
            #data = {k: convert(v) for k, v in log.items()}
            #_store_if_not_exists(chain, address, log['blockNumber'],
            #                     log['transactionIndex'], data)
            #callback(chain, address, log)
            jobs.append(pool.spawn(callback, chain, address, log))

        start_block += max_blocks + 1
        y = round(time.time() - _start, 2)
        print(
            f'[{chain}] elapsed {y}s ({round(y - x, 2)}s) so far at block {start_block}'
        )
        x = y

    gevent.joinall(jobs)
    print(f'[{chain}] it took {round(time.time() - _start, 2)}s!')
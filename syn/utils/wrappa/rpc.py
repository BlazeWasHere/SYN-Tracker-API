#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Callable, cast, List, TypeVar, Union
from datetime import datetime
from pprint import pformat
import time

from web3.exceptions import LogTopicError
from web3.types import FilterParams, LogReceipt
from hexbytes import HexBytes
from gevent.pool import Pool
import simplejson as json
from web3 import Web3
import gevent

from syn.utils.data import BRIDGE_ABI, OLDBRIDGE_ABI, SYN_DATA, LOGS_REDIS_URL, \
    OLDERBRIDGE_ABI, TOKEN_DECIMALS
from syn.utils.helpers import get_gas_stats_for_tx, handle_decimals, \
    get_airdrop_value_for_block
from syn.utils.explorer.poll import figure_out_method
from syn.utils.explorer.data import TOPICS, Direction, TOPIC_TO_EVENT

start_blocks = {
    'ethereum': 13136427,
    'arbitrum': 657404,
    'avalanche': 3376709,
    'bsc': 10065475,
    'fantom': 18503502,
    'polygon': 18026806,
    'harmony': 18646320,
    'boba': 16188,
    'moonriver': 890949,
    'optimism': 30718,
}

airdrop_ranges = {
    'polygon': {
        # +------------------------- The airdrop value in the chain's native
        # |                           token (used for paying gas fees).
        # |
        # |       +----------------- Shows this is the bridge's initial fee.
        # |       |
        # |       |    +------------ Airdrop was 0.0003 till this block
        # |       |    |              (including this block).
        # |       |    |
        # v       v    v
        0.0003: [None, 20335948],
        #      +-------------------- Airdrop was 0.02 starting from this
        #      |                       block (including this block).
        #      |
        #      |         +---------- Shows this is the airdrop value currently.
        #      |         |
        #      v         v
        0.02: [20335949, None],
    },
    'bsc': {
        0.001: [None, 12038426],
        0.002: [12038427, None],
    },
    'avalanche': {
        0.05: [None, 7164612],
        0.025: [7164613, None],
    },
    'fantom': {
        0.4: [None, None],
    },
    'moonriver': {
        0.1: [None, 914404],
        0.002: [914403, None],
    },
    'ethereum': {
        0: [None, None],
    },
    'arbitrum': {
        0: [None, None],
    },
    'harmony': {
        0.1: [None, None],
    },
    'boba': {
        0.005: [None, None],
    },
    'optimism': {
        0: [None, None],
    },
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
    tx_hash = log['transactionHash']

    block_n = log['blockNumber']
    date = w3.eth.get_block(block_n)['timestamp']  # type: ignore
    date = datetime.utcfromtimestamp(date).date()

    topic = cast(str, convert(log['topics'][0]))
    if topic not in TOPICS:
        raise RuntimeError(f'sanity check? got invalid topic: {topic}')

    direction = TOPICS[topic]
    if direction == Direction.OUT:
        # For OUT transactions the bridged asset
        # and its amount are stored in the logs data
        event = TOPIC_TO_EVENT[topic]
        try:
            data = contract.events[event]().processLog(log)
        except LogTopicError:
            if abi == OLDERBRIDGE_ABI:
                raise TypeError(log, chain)
            elif abi == OLDBRIDGE_ABI:
                abi = OLDERBRIDGE_ABI
            elif abi == BRIDGE_ABI:
                abi = OLDBRIDGE_ABI
            else:
                raise RuntimeError(f'sanity check? got invalid abi: {abi}')

            return bridge_callback(chain, address, log, abi)

        args = data['args']  # type: ignore
    elif direction == Direction.IN:
        # For IN transactions the bridged asset
        # and its amount are stored in the tx.input
        tx_info = w3.eth.get_transaction(tx_hash)

        # All IN transactions are guaranteed to be
        # from validators to Bridge contract
        _, args = contract.decode_function_input(
            tx_info['input'])  # type: ignore
    else:
        raise RuntimeError(f'sanity check? got {direction}')

    if 'token' not in args:
        raise RuntimeError(
            f'No token: chain = {chain}, tx_hash = {convert(tx_hash)}')

    asset = args['token'].lower()

    if 'chainId' in args:
        _chain = f':{args["chainId"]}'
    else:
        _chain = ''

    if asset not in TOKEN_DECIMALS[chain]:
        raise RuntimeError(
            f'Decimals? token = {asset}, tx_hash = {convert(tx_hash)}')

    decimals = TOKEN_DECIMALS[chain][asset]
    # Amount is in nUSD/nETH/SYN/etc
    value = {'amount': handle_decimals(args['amount'], decimals), 'txCount': 1}

    if direction == Direction.IN:
        # All `IN` txs are from the validator;
        # let's track how much gas they pay.
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        gas_stats = get_gas_stats_for_tx(chain, w3, tx_hash, receipt)
        value['validator'] = gas_stats

        # Let's also track how much fees the user paid for the bridge tx
        value['fees'] = handle_decimals(args['fee'], 18)

        # All `IN` txs give some airdrop amounts, well on most chains at least.
        if chain in airdrop_ranges:
            value['airdrops'] = get_airdrop_value_for_block(
                airdrop_ranges[chain], block_n)
        else:
            raise RuntimeError(f'{chain} is not in `airdrop_ranges`')

    # Just in case we ever need that later for debugging
    # value['txs'] = f'[{convert(tx_hash)}]'

    key = f'{chain}:bridge:{date}:{asset}:{direction}{_chain}'

    if (ret := LOGS_REDIS_URL.get(key)) is not None:
        ret = json.loads(ret, use_decimal=True)

        if direction == Direction.IN:
            if 'validator' not in ret:
                raise RuntimeError(
                    f'No validator for key = {key}, ret = {pformat(ret, indent=2)}'
                )
            if 'validator' not in value:
                raise RuntimeError(
                    f'No validator: chain = {chain}, tx_hash = {convert(tx_hash)}'
                )

            if chain in airdrop_ranges:
                ret['airdrops'] += value['airdrops']

            ret['validator']['gas_price'] += value['validator']['gas_price']
            ret['validator']['gas_paid'] += value['validator']['gas_paid']
            ret['fees'] += value['fees']

        ret['amount'] += value['amount']
        ret['txCount'] += 1
        # Just in case we ever need that later for debugging
        # ret['txs'] += ' ' + value['txs']

        LOGS_REDIS_URL.set(key, json.dumps(ret))
    else:
        LOGS_REDIS_URL.set(key, json.dumps(value))

    LOGS_REDIS_URL.set(f'{chain}:logs:{address}:MAX_BLOCK_STORED',
                       log['blockNumber'])
    LOGS_REDIS_URL.set(f'{chain}:logs:{address}:TX_INDEX',
                       log['transactionIndex'])


def get_logs(
    chain: str,
    callback: Callable[[str, str, LogReceipt], None],
    start_block: int = None,
    till_block: int = None,
    max_blocks: int = MAX_BLOCKS,
) -> None:
    address = SYN_DATA[chain]['bridge']
    w3: Web3 = SYN_DATA[chain]['w3']
    _chain = f'[{chain}]'
    chain_len = max(len(c) for c in SYN_DATA) + 2
    tx_index = -1

    if start_block is None:
        _key_block = f'{chain}:logs:{address}:MAX_BLOCK_STORED'
        _key_index = f'{chain}:logs:{address}:TX_INDEX'

        if (ret := LOGS_REDIS_URL.get(_key_block)) is not None:
            start_block = max(int(ret), start_blocks[chain])

            if (ret := LOGS_REDIS_URL.get(_key_index)) is not None:
                tx_index = int(ret)
        else:
            start_block = start_blocks[chain]

    if till_block is None:
        till_block = w3.eth.block_number

    print(
        f'{_chain:{chain_len}} starting from {start_block} with block height of {till_block}'
    )
    jobs: List[gevent.Greenlet] = []
    _start = time.time()
    x = 0

    total_events = 0
    initial_block = start_block

    while start_block < till_block:
        to_block = min(start_block + max_blocks, till_block)

        params: FilterParams = {
            'fromBlock': start_block,
            'toBlock': to_block,
            'address': w3.toChecksumAddress(address),
            'topics': [list(TOPICS)],  # type: ignore
        }

        logs: List[LogReceipt] = w3.eth.get_logs(params)
        for log in logs:
            # Skip transactions from the very first block
            # that are already in the DB
            if log['blockNumber'] == initial_block \
              and log['transactionIndex'] <= tx_index:
                continue

            callback(chain, address, log)

        start_block += max_blocks + 1

        y = time.time() - _start
        total_events += len(logs)

        print(f'{_chain:{chain_len}} elapsed {y:5.1f}s ({y - x:4.2f}s),'
              f' found {total_events:5} events, so far at block {start_block}')
        x = y

    gevent.joinall(jobs)
    print(f'{_chain:{chain_len}} it took {time.time() - _start:.1f}s!')

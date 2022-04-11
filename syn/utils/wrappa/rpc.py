#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Callable, Dict, cast, List, TypeVar, Union
from datetime import datetime
from pprint import pformat
import time

from web3.types import FilterParams, LogReceipt, TxData
from gevent.pool import Pool
import simplejson as json
from web3 import Web3
import gevent

from syn.utils.helpers import (get_gas_stats_for_tx, handle_decimals,
                               get_airdrop_value_for_block, convert,
                               parse_logs_out, parse_tx_in, retry)
from syn.utils.data import SYN_DATA, LOGS_REDIS_URL, TOKEN_DECIMALS
from syn.utils.explorer.data import TOPICS, Direction
from syn.utils.contract import get_bridge_token_info

_start_blocks = {
    # 'ethereum': 13136427,  # 2021-09-01
    'ethereum': 13033669,
    'arbitrum': 657404,
    'avalanche': 3376709,
    'bsc': 10065475,
    'fantom': 18503502,
    'polygon': 18026806,
    'harmony': 18646320,
    'boba': 16188,
    'moonriver': 890949,
    'optimism': 30718,
    'aurora': 56092179,
    'moonbeam': 173355,
    'cronos': 1578335,
    'metis': 957508,
    'dfk': 0,  # Doesn't it feel great to be the first?
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
        0.002: [914405, None],
    },
    'ethereum': {
        0: [None, None],
    },
    'arbitrum': {
        0: [None, 3393884],
        0.003: [3393885, None],
    },
    'harmony': {
        0.1: [None, None],
    },
    'boba': {
        0.005: [None, None],
    },
    'optimism': {
        0: [None, 541401],
        0.002: [541402, None],
    },
    'aurora': {
        # Currenty 0 gas needed for txs on Aurora.
        0: [None, None],
    },
    'moonbeam': {
        0: [None, None],
    },
    'cronos': {
        0: [None, None],
    },
    'metis': {
        0: [None, 1293668],
        0.02: [1293669, None],
    },
    'dfk': {
        0: [None, 408],
        0.01: [409, None],
    },
}

pool = Pool(size=64)
MAX_BLOCKS = 5000
T = TypeVar('T')


def bridge_callback(chain: str, address: str, log: LogReceipt,
                    first_run: bool) -> None:
    w3: Web3 = SYN_DATA[chain]['w3']
    tx_hash = log['transactionHash']

    block_n = log['blockNumber']
    timestamp = w3.eth.get_block(block_n)['timestamp']  # type: ignore
    date = datetime.utcfromtimestamp(timestamp).date()

    topic = cast(str, convert(log['topics'][0]))
    if topic not in TOPICS:
        raise RuntimeError(f'sanity check? got invalid topic: {topic}')

    args: Dict[str, Union[int, str]]
    direction = TOPICS[topic]
    if direction == Direction.OUT:
        # For OUT transactions the bridged asset
        # and its amount are stored in the logs data
        args = parse_logs_out(log)
    elif direction == Direction.IN:
        # For IN transactions the bridged asset
        # and its amount are stored in the tx.input
        tx_data: TxData = w3.eth.get_transaction(tx_hash)

        # All IN transactions are guaranteed to be
        # from validators to Bridge contract
        args = parse_tx_in(tx_data)
    else:
        raise RuntimeError(f'sanity check? got {direction}')

    if 'token' not in args:
        raise RuntimeError(
            f'No token: chain = {chain}, tx_hash = {convert(tx_hash)}')

    asset = cast(str, args['token']).lower()

    if 'chain_id' in args:
        _chain = f':{args["chain_id"]}'
    else:
        _chain = ''

    if asset not in TOKEN_DECIMALS[chain]:
        ret = get_bridge_token_info(chain, asset)

        if not ret:
            if direction == Direction.IN:
                # All IN txs are with supported tokens.
                print(f'failed to add new token: {chain} {asset}')
            else:
                # Someone tried to bridge an unsupported token - ignore it.
                print(
                    f'unsupported bridge token: {chain} {tx_hash.hex()}',
                    asset,
                )

            return
        else:
            print(f'new token {chain} {asset} {ret}')
            TOKEN_DECIMALS[chain].update({asset.lower(): ret[2]})

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
        # NOTE: we push this into the bridge callback rather than it's own
        # callback to save some rpc calls, why can't they be free? *sigh*.
        # First bridge tx of the day; store this block so we can later map
        # date to block, which is a limitation of eth rpc. However this should
        # not get confused with the FIRST block of the day, rather it is the
        # first block of the day which contains a bridge event.
        _key = f'{chain}:date2block:{date}'
        LOGS_REDIS_URL.setnx(
            _key, json.dumps({
                'block': block_n,
                'timestamp': timestamp,
            }))

        LOGS_REDIS_URL.set(key, json.dumps(value))

    LOGS_REDIS_URL.set(f'{chain}:logs:{address}:MAX_BLOCK_STORED',
                       log['blockNumber'])
    LOGS_REDIS_URL.set(f'{chain}:logs:{address}:TX_INDEX',
                       log['transactionIndex'])


def get_logs(
    chain: str,
    callback: Callable[[str, str, LogReceipt, bool], None],
    address: str,
    start_block: int = None,
    till_block: int = None,
    max_blocks: int = MAX_BLOCKS,
    topics: List[str] = list(TOPICS),
    key_namespace: str = 'logs',
    start_blocks: Dict[str, int] = _start_blocks,
    prefer_db_values: bool = True,
) -> None:
    w3: Web3 = SYN_DATA[chain]['w3']
    _chain = f'[{chain}]'
    chain_len = max(len(c) for c in SYN_DATA) + 2
    tx_index = -1

    if start_block is None or prefer_db_values:
        _key_block = f'{chain}:{key_namespace}:{address}:MAX_BLOCK_STORED'
        _key_index = f'{chain}:{key_namespace}:{address}:TX_INDEX'

        if (ret := LOGS_REDIS_URL.get(_key_block)) is not None:
            _start_block = max(int(ret), start_blocks[chain])

            if (ret := LOGS_REDIS_URL.get(_key_index)) is not None:
                tx_index = int(ret)
        else:
            _start_block = start_blocks[chain]

        if start_block is not None and prefer_db_values:
            # We don't want to go back in blocks we already checked.
            start_block = max(_start_block, start_block)
        else:
            start_block = _start_block

    if till_block is None:
        till_block = w3.eth.block_number

    print(
        f'{key_namespace} | {_chain:{chain_len}} starting from {start_block} '
        f'with block height of {till_block}')

    jobs: List[gevent.Greenlet] = []
    _start = time.time()
    x = 0

    total_events = 0
    initial_block = start_block
    first_run = True

    while start_block < till_block:
        to_block = min(start_block + max_blocks, till_block)

        params: FilterParams = {
            'fromBlock': start_block,
            'toBlock': to_block,
            'address': w3.toChecksumAddress(address),
            'topics': [topics],  # type: ignore
        }

        logs: List[LogReceipt] = retry(w3.eth.get_logs, params)

        # Apparently, some RPC nodes don't bother
        # sorting events in a chronological order.
        # Let's sort them by block (from oldest to newest)
        # And by transaction index (within the same block,
        # also in ascending order)
        logs = sorted(logs,
                      key=lambda k: (k['blockNumber'], k['transactionIndex']))

        for log in logs:
            # Skip transactions from the very first block
            # that are already in the DB
            if log['blockNumber'] == initial_block \
              and log['transactionIndex'] <= tx_index:
                continue

            try:
                retry(callback, chain, address, log, first_run)
            except Exception as e:
                print(chain, log)
                raise e

            if first_run:
                first_run = False

        start_block += max_blocks + 1

        y = time.time() - _start
        total_events += len(logs)

        percent = 100 * (to_block - initial_block) \
            / (till_block - initial_block)

        print(f'{key_namespace} | {_chain:{chain_len}} elapsed {y:5.1f}s'
              f' ({y - x:5.1f}s), found {total_events:5} events,'
              f' {percent:4.1f}% done: so far at block {start_block}')
        x = y

    gevent.joinall(jobs)
    print(f'{_chain:{chain_len}} it took {time.time() - _start:.1f}s!')

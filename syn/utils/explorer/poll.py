#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import List, Callable

from web3.datastructures import AttributeDict
from web3.contract import Contract
from web3.logs import DISCARD
from gevent.pool import Pool
from gevent import Greenlet
from web3 import Web3
import gevent

from syn.utils.explorer.data import EVENTS, TOPICS, Direction
from syn.utils.data import BRIDGE_ABI, SYN_DATA

CB = Callable[[AttributeDict, str, AttributeDict, str, Direction], None]
pool = Pool()


def figure_out_method(contract: Contract, receipt):
    for k, v in EVENTS.items():
        ret = contract.events[k]().processReceipt(receipt, errors=DISCARD)

        if ret:
            return ret, v, k


def handle_event(event: AttributeDict, chain: str, contract: Contract,
                 cb: CB) -> None:
    try:
        receipt = SYN_DATA[chain]['w3'].eth.waitForTransactionReceipt(
            event['transactionHash'], timeout=10)
    except:
        print(chain, event)
        raise

    try:
        data, direction, method = figure_out_method(contract,
                                                    receipt)  # type: ignore
    except:
        print(chain, event)
        raise

    data = data[0]['args']
    cb(event, chain, data, method, direction)


def log_loop(filter, chain: str, contract: Contract, poll: int, cb: CB):
    while True:
        for event in filter.get_new_entries():
            # print(chain, event)
            handle_event(event, chain, contract, cb)

        gevent.sleep(poll)


def start(cb: CB):
    jobs: List[Greenlet] = []

    for chain, x in SYN_DATA.items():
        _address = Web3.toChecksumAddress(x['bridge'])

        filter = x['w3'].eth.filter({
            'address': _address,
            'fromBlock': 'latest',
            'topics': [list(TOPICS)],
        })

        jobs.append(
            pool.spawn(log_loop,
                       filter,
                       chain,
                       x['w3'].eth.contract(_address, abi=BRIDGE_ABI),
                       poll=2,
                       cb=cb))

    # This will never sanely finish.
    gevent.joinall(jobs)

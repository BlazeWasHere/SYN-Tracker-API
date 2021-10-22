#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import List

from flask import jsonify, Blueprint
from gevent.greenlet import Greenlet
from gevent.pool import Pool
from web3 import Web3
import gevent

from syn.utils.cache import timed_cache

TOTAL_SUPPLY_ABI = """[{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"}]"""
SYN_DECIMALS = 18
SYN_DATA = {
    "ethereum": {
        "rpc":
        "https://eth-mainnet.alchemyapi.io/v2/0AovFRYl9L7l4YUf6nPaMrs7H2_pj_Pf",
        "address": "0x0f2D719407FdBeFF09D87557AbB7232601FD9F29",
    },
    "avalanche": {
        "rpc": "https://api.avax.network/ext/bc/C/rpc",
        "address": "0x1f1E7c893855525b303f99bDF5c3c05Be09ca251",
    },
    "bsc": {
        "rpc": "https://bsc-dataseed.binance.org",
        "address": "0xa4080f1778e69467e905b8d6f72f6e441f9e9484",
    },
    "polygon": {
        "rpc": "https://rpc-mainnet.matic.network",
        "address": "0xf8f9efc0db77d8881500bb06ff5d6abc3070e695",
    },
    "arbitrum": {
        "rpc": "https://arb1.arbitrum.io/rpc",
        "address": "0x080f6aed32fc474dd5717105dba5ea57268f46eb",
    },
    "fantom": {
        "rpc": "https://rpc.ftm.tools",
        "address": "0xe55e19fb4f2d85af758950957714292dac1e25b2",
    }
}

circ_bp = Blueprint('circ_bp', __name__)
pool = Pool()

# Init 'func' to append `contract` to SYN_DATA so we can call the ABI simpler later.
for key, value in SYN_DATA.items():
    w3 = Web3(Web3.HTTPProvider(value['rpc']))
    value.update({
        'contract':
        w3.eth.contract(Web3.toChecksumAddress(value['address']),
                        abi=TOTAL_SUPPLY_ABI)  # type: ignore
    })


@timed_cache(60)
def get_chain_circ_cupply(chain: str) -> float:
    assert (chain in SYN_DATA)
    return SYN_DATA[chain]['contract'].functions.totalSupply(  # type: ignore
    ).call() / 10**SYN_DECIMALS


@timed_cache(60 * 30)
def get_all_chains_circ_supply() -> float:
    jobs: List[Greenlet] = []
    total: float = 0

    for chain in SYN_DATA:
        jobs.append(pool.spawn(get_chain_circ_cupply, chain))

    ret: List[Greenlet] = gevent.joinall(jobs)
    for x in ret:
        total += x.get()

    return total


@circ_bp.route('/', methods=['GET'])
def circ():
    return jsonify({'supply': get_all_chains_circ_supply()})


@circ_bp.route('/<chain>', methods=['GET'])
def circ_chain(chain: str):
    if chain not in SYN_DATA:
        return (jsonify({
            'error': 'invalid chain',
            'valids': list(SYN_DATA),
        }), 400)

    return jsonify({'supply': get_chain_circ_cupply(chain)})
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
import gevent

from syn.utils.data import SYN_DATA, SYN_DECIMALS
from syn.utils.cache import timed_cache

circ_bp = Blueprint('circ_bp', __name__)
pool = Pool()


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
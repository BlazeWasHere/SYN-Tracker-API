#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from decimal import Decimal
from typing import List

from flask import jsonify, Blueprint
from gevent.greenlet import Greenlet
from gevent.pool import Pool
import gevent

from syn.utils.data import SYN_DATA, SYN_DECIMALS, cache
from syn.utils.helpers import handle_decimals, raise_if
from syn.utils.cache import timed_cache
from syn.utils.contract import call_abi

circ_bp = Blueprint('circ_bp', __name__)
pool = Pool()


@timed_cache(60)
def get_chain_circ_cupply(chain: str) -> Decimal:
    return handle_decimals(
        call_abi(SYN_DATA[chain], 'contract', 'totalSupply'), SYN_DECIMALS)


@timed_cache(60 * 30)
def get_all_chains_circ_supply() -> Decimal:
    jobs: List[Greenlet] = []
    total: Decimal = Decimal(0)

    for chain in SYN_DATA:
        jobs.append(pool.spawn(get_chain_circ_cupply, chain))

    ret: List[Greenlet] = gevent.joinall(jobs)
    for x in ret:
        total += raise_if(x.get(), None)

    return total


@circ_bp.route('/', methods=['GET'])
@cache.cached()
def circ():
    return jsonify({'supply': get_all_chains_circ_supply()})


@circ_bp.route('/<chain:chain>', methods=['GET'])
@cache.cached()
def circ_chain(chain: str):
    return jsonify({'supply': get_chain_circ_cupply(chain)})
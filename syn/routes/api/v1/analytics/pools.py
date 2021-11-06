#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from datetime import datetime
from typing import Dict, List

from web3.exceptions import BadFunctionCallOutput
from flask import Blueprint, jsonify, request
from gevent.greenlet import Greenlet
from gevent.pool import Pool
import gevent

from syn.utils.data import SYN_DATA, cache, _forced_update, REDIS
from syn.utils.analytics.nusd import get_virtual_price
from syn.utils import verify

pools_bp = Blueprint('pools_bp', __name__)

# 15m
TIMEOUT = 60 * 15
gpool = Pool()
metapools = list(SYN_DATA)
# No metapool on ETH.
metapools.remove('ethereum')

basepools = list(SYN_DATA)

pools = ['metapool', 'basepool']


@pools_bp.route('/<pool>/price/virtual/<chain>', methods=['GET'])
@cache.cached(timeout=TIMEOUT, forced_update=_forced_update, query_string=True)
def price_virtual_chain(pool: str, chain: str):
    chains = metapools if pool == 'metapool' else basepools

    if pool not in pools:
        return (jsonify({'error': 'invalid pool', 'valids': pools}), 400)
    elif chain not in chains:
        return (jsonify({
            'error': 'invalid chain',
            'valids': chains,
        }), 400)

    block = request.args.get('block', 'latest')
    if block != 'latest':
        if not verify.isdigit(block):
            return (jsonify({'error': 'invalid block num'}), 400)

        block = int(block)

    func = 'metapool_contract' if pool == 'metapool' else 'basepool_contract'

    try:
        return jsonify(get_virtual_price(chain, block, func=func))
    except BadFunctionCallOutput:
        return (jsonify({'error': 'contract not deployed'}), 400)


@pools_bp.route('/<pool>/price/virtual', methods=['GET'])
@cache.cached(timeout=TIMEOUT, forced_update=_forced_update)
def price_virtual(pool: str):
    from syn.utils.helpers import raise_if

    chains = metapools if pool == 'metapool' else basepools

    if pool not in pools:
        return (jsonify({'error': 'invalid pool', 'valids': pools}), 400)

    res: Dict[str, float] = {}
    jobs: List[Greenlet] = []

    func = 'metapool_contract' if pool == 'metapool' else 'basepool_contract'

    for chain in chains:
        jobs.append(gpool.spawn(get_virtual_price, chain, 'latest', func=func))

    ret: List[Greenlet] = gevent.joinall(jobs)
    for x in ret:
        res.update(raise_if(x.get(), None))

    return jsonify(res)


@pools_bp.route('/<pool>/price/virtual/<chain>/<date:date>', methods=['GET'])
@cache.cached(forced_update=_forced_update)
def price_virtual_chain_historical(pool: str, chain: str, date: datetime):
    chains = metapools if pool == 'metapool' else basepools

    if pool not in pools:
        return (jsonify({'error': 'invalid pool', 'valids': pools}), 400)
    elif chain not in chains:
        return (jsonify({
            'error': 'invalid chain',
            'valids': chains,
        }), 400)

    ret = verify.is_sane_date(date)
    if ret != True:
        return (jsonify({'error': ret, 'valids': []}), 400)

    _date = str(date.date())
    return jsonify({_date: REDIS.get(f'{pool}:{chain}:vp:{_date}')})

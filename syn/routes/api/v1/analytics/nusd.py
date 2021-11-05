#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Dict, List

from flask import Blueprint, jsonify, request
from gevent.greenlet import Greenlet
from gevent.pool import Pool
import gevent

from syn.utils.data import SYN_DATA, cache, _forced_update
from syn.utils.analytics.nusd import get_virtual_price
from syn.utils.helpers import raise_if
from syn.utils import verify

nusd_bp = Blueprint('nusd_bp', __name__)

# 15m
TIMEOUT = 60 * 15
pool = Pool()
_list = list(SYN_DATA)
# No metapool on ETH.
_list.remove('ethereum')


@nusd_bp.route('/price/', defaults={'chain': ''}, methods=['GET'])
@nusd_bp.route('/price/<chain>', methods=['GET'])
@cache.cached(timeout=TIMEOUT, forced_update=_forced_update, query_string=True)
def nusd_price_chain(chain: str):
    if chain not in _list:
        return (jsonify({
            'error': 'invalid chain',
            'valids': _list,
        }), 400)

    block = request.args.get('block', 'latest')
    if block != 'latest':
        if not verify.isdigit(block):
            return (jsonify({'error': 'invalid block num'}), 400)

        block = int(block)

    return jsonify(get_virtual_price(chain, block))


@nusd_bp.route('/price', methods=['GET'])
@cache.cached(timeout=TIMEOUT, forced_update=_forced_update)
def nusd_price():
    res: Dict[str, float] = {}
    jobs: List[Greenlet] = []

    for chain in _list:
        jobs.append(pool.spawn(get_virtual_price, chain, 'latest'))

    ret: List[Greenlet] = gevent.joinall(jobs)
    for x in ret:
        res.update(raise_if(x.get(), None))

    return jsonify(res)

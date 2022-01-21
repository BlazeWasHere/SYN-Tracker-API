#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Any, Dict, List, Union, get_args
from collections import defaultdict
from itertools import chain
from decimal import Decimal

from web3.exceptions import BadFunctionCallOutput
from flask import Blueprint, jsonify, request
from gevent.greenlet import Greenlet
from gevent.pool import Pool
import gevent

from syn.utils.analytics.pool import Pools, get_swap_volume_for_pool
from syn.utils.contract import get_virtual_price
from syn.utils.data import SYN_DATA, cache
from syn.utils.helpers import raise_if
from syn.utils import verify

pools_bp = Blueprint('pools_bp', __name__)

# 15m
TIMEOUT = 60 * 15
gpool = Pool()


def _dispatch(chain: str, block: Union[str, int]) -> List[Greenlet]:
    threads: List[Greenlet] = []

    if 'pool_contract' in SYN_DATA[chain]:
        threads.append(
            gpool.spawn(get_virtual_price, chain, block, 'pool_contract'))

    if 'ethpool_contract' in SYN_DATA[chain]:
        threads.append(
            gpool.spawn(get_virtual_price, chain, block, 'ethpool_contract'))

    return threads


def _convert_ret(ret: Dict[str, Any], res: Dict[str, Decimal]) -> None:
    if 'ethpool_contract' in ret:
        res['neth'] = ret['ethpool_contract']
    elif 'pool_contract' in ret:
        res['nusd'] = ret['pool_contract']


@pools_bp.route('/price/virtual/<chain:chain>', methods=['GET'])
@cache.cached(timeout=TIMEOUT, query_string=True)
def price_virtual_chain(chain: str):
    block = request.args.get('block', 'latest')
    if block != 'latest':
        if not verify.isdigit(block):
            return (jsonify({'error': 'invalid block num'}), 400)

        block = int(block)

    threads: List[Greenlet] = _dispatch(chain, block)
    res: Dict[str, Decimal] = {}
    gevent.joinall(threads)

    for thread in threads:
        _convert_ret(raise_if(thread.get(), None)[chain], res)

    try:
        return jsonify(res)
    except BadFunctionCallOutput:
        return (jsonify({'error': 'contract not deployed'}), 400)


@pools_bp.route('/price/virtual', methods=['GET'])
@cache.cached(timeout=TIMEOUT)
def price_virtual():
    res: Dict[str, Dict[str, Decimal]] = defaultdict(dict)
    jobs: Dict[str, List[Greenlet]] = {}

    for _chain in SYN_DATA:
        assert _chain not in jobs
        jobs[_chain] = _dispatch(_chain, 'latest')

    gevent.joinall(list(chain.from_iterable(jobs.values())))
    for k, v in jobs.items():
        for x in v:
            _convert_ret(raise_if(x.get(), None)[k], res[k])

    return jsonify(res)


@pools_bp.route('/volume/<chain:chain>/',
                defaults={'pool': ''},
                methods=['GET'])
@pools_bp.route('/volume/<chain:chain>/<pool>', methods=['GET'])
@cache.cached(timeout=TIMEOUT)
def volume_pool(chain: str, pool: Pools):
    if pool not in get_args(Pools):
        return (jsonify({
            'error': 'invalid pool',
            'valids': get_args(Pools),
        }), 400)

    return jsonify(get_swap_volume_for_pool(pool, chain))


#@pools_bp.route('/price/virtual/<chain>/<date:date>', methods=['GET'])
#@cache.cached()
#def price_virtual_chain_historical(chain: str, date: datetime):
#    if chain not in SYN_DATA:
#        return (jsonify({
#            'error': 'invalid chain',
#            'valids': list(SYN_DATA),
#        }), 400)
#
#    ret = verify.is_sane_date(date)
#    if ret != True:
#        return (jsonify({'error': ret, 'valids': []}), 400)
#
#    _date = str(date.date())
#    return jsonify({_date: REDIS.get(f'pools:{chain}:vp:{_date}')})

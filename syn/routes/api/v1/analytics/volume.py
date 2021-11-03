#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Any, Callable, Dict, List

from flask import Blueprint, jsonify
from gevent.greenlet import Greenlet
from gevent.pool import Pool
import gevent

from syn.utils.analytics.volume import get_chain_volume, get_chain_volume_covalent
from syn.utils.data import BRIDGES, NULL_ADDR, SYN_DATA, DEFILLAMA_DATA, cache, \
    DEFAULT_TIMEOUT, _forced_update
from syn.utils.helpers import merge_many_dicts, raise_if, \
    store_volume_dict_to_redis

pool = Pool()

volume_bp = Blueprint('volume_bp', __name__)
ETH_TOKENS = ['nusd', 'syn', 'high', 'dog', 'usdt', 'usdc', 'dai']
BSC_TOKENS = ['nusd', 'syn', 'high', 'dog']
POLYGON_TOKENS = ['nusd', 'syn']


def filter_factory(key: str,
                   chain: str,
                   address: str = '') -> Callable[[Dict[str, str]], bool]:
    if not address:
        if chain == 'ethereum':
            address = DEFILLAMA_DATA['bridges'][chain]['metaswap']
        else:
            address = SYN_DATA[chain]['metapool']

    def filter(x: Dict[str, str]) -> bool:
        return x['to_address'] == address.lower() \
            and x['address'] == SYN_DATA[chain][key].lower()

    return filter


def esc_filter_factory(chain: str,
                       c_address: str) -> Callable[[Dict[str, Any]], bool]:
    def filter(data: Dict[str, Any]) -> bool:
        if data['to_address'] not in BRIDGES[chain]:
            return False

        for x in data['transfers']:
            if x['contract_address'] == c_address.lower():
                return True

        return False

    return filter


@volume_bp.route('/ethereum', methods=['GET'])
@cache.cached(timeout=DEFAULT_TIMEOUT, forced_update=_forced_update)
def volume_eth():
    address = DEFILLAMA_DATA['bridges']['ethereum']['metaswap']
    resps: List[Dict[str, Any]] = []
    jobs: List[Greenlet] = []

    def _dispatch(*args, **kwargs):
        return get_chain_volume(*args, **kwargs)

    for x in ETH_TOKENS:
        x = 'address' if x == 'syn' else x
        jobs.append(
            pool.spawn(_dispatch, address, 'eth',
                       filter_factory(x, 'ethereum')))

    ret: List[Greenlet] = gevent.joinall(jobs)
    for x in ret:
        resps.append(raise_if(x.get(), None))

    return jsonify(merge_many_dicts(resps, is_price_dict=True))


@volume_bp.route('/ethereum/filter/', defaults={'token': ''}, methods=['GET'])
@volume_bp.route('/ethereum/filter/<token>', methods=['GET'])
@cache.cached(timeout=DEFAULT_TIMEOUT, forced_update=_forced_update)
def volume_eth_filter(token: str):
    if token not in ETH_TOKENS:
        return (jsonify({
            'error': 'invalid token',
            'valids': ETH_TOKENS,
        }), 400)
    elif token == 'syn':
        token = 'address'

    address = DEFILLAMA_DATA['bridges']['ethereum']['metaswap']
    ret = get_chain_volume(address, 'eth', filter_factory(token, 'ethereum'))
    pool.spawn(store_volume_dict_to_redis, 'ethereum', ret)

    return jsonify(ret)


@volume_bp.route('/bsc', methods=['GET'])
@cache.cached(timeout=DEFAULT_TIMEOUT, forced_update=_forced_update)
def volume_bsc():
    resps: List[Dict[str, Any]] = []
    jobs: List[Greenlet] = []

    def _dispatch(*args, **kwargs):
        return get_chain_volume_covalent(*args, **kwargs)

    for x in BSC_TOKENS:
        c_address = SYN_DATA['bsc']['address' if x == 'syn' else x]
        jobs.append(
            pool.spawn(_dispatch, NULL_ADDR, c_address, 'bsc',
                       esc_filter_factory('bsc', c_address)))

    ret: List[Greenlet] = gevent.joinall(jobs)
    for x in ret:
        resps.append(raise_if(x.get(), None))

    return jsonify(merge_many_dicts(resps, is_price_dict=True))


@volume_bp.route('/bsc/filter/', defaults={'token': ''}, methods=['GET'])
@volume_bp.route('/bsc/filter/<token>', methods=['GET'])
@cache.cached(timeout=DEFAULT_TIMEOUT, forced_update=_forced_update)
def volume_bsc_filter(token: str):
    if token not in BSC_TOKENS:
        return (jsonify({
            'error': 'invalid token',
            'valids': BSC_TOKENS,
        }), 400)
    elif token == 'syn':
        token = 'address'

    c_address = SYN_DATA['bsc'][token]
    ret = get_chain_volume_covalent(NULL_ADDR, c_address, 'bsc',
                                    esc_filter_factory('bsc', c_address))
    pool.spawn(store_volume_dict_to_redis, 'bsc', ret)

    return jsonify(ret)


# TODO: finish this off.
@volume_bp.route('/polygon/filter/', defaults={'token': ''}, methods=['GET'])
@volume_bp.route('/polygon/filter/<token>', methods=['GET'])
def volume_polygon_filter(token: str):
    if token not in POLYGON_TOKENS:
        return (jsonify({
            'error': 'invalid token',
            'valids': POLYGON_TOKENS,
        }), 400)
    elif token == 'syn':
        token = 'address'

    c_address = SYN_DATA['polygon'][token]
    return jsonify(
        get_chain_volume_covalent(NULL_ADDR, c_address, 'polygon',
                                  esc_filter_factory('polygon', c_address)))

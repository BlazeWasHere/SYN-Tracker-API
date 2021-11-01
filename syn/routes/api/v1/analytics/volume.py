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
from syn.utils.data import NULL_ADDR, SYN_DATA, DEFILLAMA_DATA
from syn.utils.helpers import merge_many_dicts, raise_if

pool = Pool()

volume_bp = Blueprint('volume_bp', __name__)
ETH_TOKENS = ['nusd', 'syn', 'high', 'dog', 'usdt', 'usdc', 'dai']
BSC_TOKENS = ['nusd', 'syn', 'high', 'dog']


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


def bsc_filter_factory(c_address: str) -> Callable[[Dict[str, Any]], bool]:
    def filter(data: Dict[str, Any]) -> bool:
        _bridges = [
            # BSC Bridge
            '0xd123f70ae324d34a9e76b67a27bf77593ba8749f',
            # BSC Bridge Zap
            '0x612f3a0226463599ccbcabff89623904ef38bcb9',
            # BSC Meta Bridge Zap
            '0x8027a7fa5753c8873e130f1205da9fb8691726ab',
        ]

        if data['to_address'] not in _bridges:
            return False

        for x in data['transfers']:
            if x['contract_address'] == c_address.lower():
                return True

        return False

    return filter


@volume_bp.route('/ethereum', methods=['GET'])
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
def volume_eth_filter(token: str):
    if token not in ETH_TOKENS:
        return (jsonify({
            'error': 'invalid token',
            'valids': ETH_TOKENS,
        }), 400)
    elif token == 'syn':
        token = 'address'

    address = DEFILLAMA_DATA['bridges']['ethereum']['metaswap']
    return jsonify(
        get_chain_volume(address, 'eth', filter_factory(token, 'ethereum')))


@volume_bp.route('/bsc', methods=['GET'])
def volume_bsc():
    resps: List[Dict[str, Any]] = []
    jobs: List[Greenlet] = []

    def _dispatch(*args, **kwargs):
        return get_chain_volume_covalent(*args, **kwargs)

    for x in BSC_TOKENS:
        c_address = SYN_DATA['bsc']['address' if x == 'syn' else x]
        jobs.append(
            pool.spawn(_dispatch, NULL_ADDR, c_address, 'bsc',
                       bsc_filter_factory(c_address)))

    ret: List[Greenlet] = gevent.joinall(jobs)
    for x in ret:
        resps.append(raise_if(x.get(), None))

    return jsonify(merge_many_dicts(resps, is_price_dict=True))


@volume_bp.route('/bsc/filter/', defaults={'token': ''}, methods=['GET'])
@volume_bp.route('/bsc/filter/<token>', methods=['GET'])
def volume_bsc_filter(token: str):
    if token not in BSC_TOKENS:
        return (jsonify({
            'error': 'invalid token',
            'valids': BSC_TOKENS,
        }), 400)
    elif token == 'syn':
        token = 'address'

    c_address = SYN_DATA['bsc'][token]
    return jsonify(
        get_chain_volume_covalent(NULL_ADDR, c_address, 'bsc',
                                  bsc_filter_factory(c_address)))

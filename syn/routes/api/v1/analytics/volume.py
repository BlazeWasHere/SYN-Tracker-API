#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from collections import defaultdict
from typing import Dict

from flask import Blueprint, jsonify

from syn.utils.analytics.volume import get_chain_volume_for_address, \
    get_chain_metapool_volume, get_chain_volume, get_chain_volume_total
from syn.utils.data import SYN_DATA, cache, DEFAULT_TIMEOUT, _forced_update, \
    TOKENS_INFO

volume_bp = Blueprint('volume_bp', __name__)

symbol_to_address: Dict[str, Dict[str, str]] = defaultdict(dict)

# `symbol_to_address` is an abstraction of `TOKENS_INFO`
for chain, v in TOKENS_INFO.items():
    for token, data in v.items():
        assert token not in symbol_to_address[chain], \
            f'duped token? {token} @ {chain} | {symbol_to_address[chain][token]}'

        symbol_to_address[chain].update({data['symbol'].lower(): token})


@volume_bp.route('/<chain:chain>/filter/<token>/<direction>', methods=['GET'])
@cache.cached(timeout=60 * 5, forced_update=_forced_update)
def chain_filter_token_direction(chain: str, token: str, direction: str):
    if direction.upper() not in ['IN', 'OUT']:
        return (jsonify({
            'error': 'invalid direction',
            'valids': ['in', 'out'],
        }), 400)
    elif token not in symbol_to_address[chain]:
        return (jsonify({
            'error': 'invalid token',
            'valids': list(symbol_to_address[chain]),
        }), 400)

    if direction.upper() == 'OUT':
        direction = 'OUT:*'

    ret = get_chain_volume_for_address(symbol_to_address[chain][token], chain,
                                       direction.upper())
    return jsonify(ret)


@volume_bp.route('/<chain:chain>/',
                 defaults={'direction': ''},
                 methods=['GET'])
@volume_bp.route('/<chain:chain>/<direction>', methods=['GET'])
@cache.cached(timeout=60 * 5, forced_update=_forced_update)
def chain_volume(chain: str, direction: str):
    if direction.upper() not in ['IN', 'OUT']:
        return (jsonify({
            'error': 'invalid direction',
            'valids': ['in', 'out'],
        }), 400)

    if direction.upper() == 'OUT':
        direction = 'OUT:*'

    return jsonify(get_chain_volume(chain, direction.upper()))


@volume_bp.route('/total', methods=['GET'])
@cache.cached(timeout=60 * 5, forced_update=_forced_update)
def chain_volume_total():
    return jsonify(get_chain_volume_total())


@volume_bp.route('/metapool/', defaults={'chain': ''}, methods=['GET'])
@volume_bp.route('/metapool/<chain:chain>', methods=['GET'])
@cache.cached(timeout=DEFAULT_TIMEOUT, forced_update=_forced_update)
def volume_metapool(chain: str):
    valid_chains = list(SYN_DATA)
    valid_chains.remove('ethereum')
    valid_chains.remove('harmony')

    if chain not in valid_chains:
        return (jsonify({
            'error': f'invalid chain: {chain}',
            'valids': valid_chains,
        }), 400)

    metapool = SYN_DATA[chain]['pool']
    nusd = SYN_DATA[chain]['nusd']
    usdlp = SYN_DATA[chain]['usdlp']

    return jsonify(get_chain_metapool_volume(metapool, nusd, usdlp, chain))

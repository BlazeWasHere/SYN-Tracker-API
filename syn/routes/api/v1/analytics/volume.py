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
    get_chain_volume, get_chain_volume_total, get_chain_tx_count_total
from syn.utils.data import cache, TOKENS_INFO

volume_bp = Blueprint('volume_bp', __name__)

symbol_to_address: Dict[str, Dict[str, str]] = defaultdict(dict)

# `symbol_to_address` is an abstraction of `TOKENS_INFO`
for chain, v in TOKENS_INFO.items():
    for token, data in v.items():
        assert token not in symbol_to_address[chain], \
            f'duped token? {token} @ {chain} | {symbol_to_address[chain][token]}'

        # Skip GMX wrapper - use GMX instead.
        if chain == 'avalanche' and token == '0x20a9dc684b4d0407ef8c9a302beaaa18ee15f656':
            continue

        symbol_to_address[chain].update({data['symbol'].lower(): token})


@volume_bp.route('/<chain:chain>/filter/<token>/<direction>', methods=['GET'])
@cache.cached(timeout=60 * 5)
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
@cache.cached()
def chain_volume(chain: str, direction: str):
    if direction.upper() not in ['IN', 'OUT']:
        return (jsonify({
            'error': 'invalid direction',
            'valids': ['in', 'out'],
        }), 400)

    return jsonify(get_chain_volume(chain, direction.upper()))


@volume_bp.route('/total', methods=['GET'])
@volume_bp.route('/total/in', methods=['GET'])
@cache.cached()
def chain_volume_total():
    return jsonify(get_chain_volume_total(direction='IN'))


@volume_bp.route('/total/out', methods=['GET'])
@cache.cached()
def chain_volume_total_out():
    return jsonify(get_chain_volume_total(direction='OUT'))


@volume_bp.route('/total/tx_count', methods=['GET'])
@volume_bp.route('/total/tx_count/in', methods=['GET'])
@cache.cached()
def chain_tx_count_total():
    return jsonify(get_chain_tx_count_total(direction='IN'))


@volume_bp.route('/total/tx_count/out', methods=['GET'])
@cache.cached()
def chain_tx_count_total_out():
    return jsonify(get_chain_tx_count_total(direction='OUT'))

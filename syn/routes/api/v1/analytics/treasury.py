#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from flask import Blueprint, jsonify, request

from syn.utils.analytics.treasury import get_treasury_erc20_balances, get_treasury_erc20_balances_usd
from syn.utils.data import TREASURY, cache, _forced_update
from syn.utils import verify

treasury_bp = Blueprint('treasury_bp', __name__)

# 15m
TIMEOUT = 60 * 15


@treasury_bp.route('/<chain>', methods=['GET'])
@cache.cached(timeout=TIMEOUT, forced_update=_forced_update, query_string=True)
def treasury_chain(chain: str):
    _list = list(TREASURY.keys())
    if chain not in TREASURY:
        return (jsonify({
            'error': 'invalid chain',
            'valids': list(TREASURY.keys()),
        }), 400)

    block = request.args.get('block', 'latest')
    if block != 'latest':
        if not verify.isdigit(block):
            return (jsonify({'error': 'invalid block num'}), 400)

        block = int(block)

    ret = get_treasury_erc20_balances_usd(chain, block)
    ret['total'] = sum([x['usd'] for x in ret.values()])  # type: ignore

    return jsonify(ret)
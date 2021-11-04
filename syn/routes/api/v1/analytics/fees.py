#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from web3.exceptions import BadFunctionCallOutput
from flask import Blueprint, jsonify, request

from syn.utils.data import SYN_DATA, cache, _forced_update
from syn.utils.analytics.fees import get_admin_fees
from syn.utils import verify

fees_bp = Blueprint('fees_bp', __name__)

# 15m
TIMEOUT = 60 * 15


@fees_bp.route('/admin/', defaults={'chain': ''}, methods=['GET'])
@fees_bp.route('/admin/<chain>', methods=['GET'])
@cache.cached(timeout=TIMEOUT, forced_update=_forced_update, query_string=True)
def adminfees_chain(chain: str):
    chainzzz = list(SYN_DATA)
    chainzzz.remove('harmony')

    if chain not in chainzzz:
        return (jsonify({
            'error': 'invalid chain',
            'valids': chainzzz,
        }), 400)

    # TODO(blaze): On some RPC nodes they limit past blocks and this throws
    # an error messily here.
    block = request.args.get('block', 'latest')
    if block != 'latest':
        if not verify.isdigit(block):
            return (jsonify({'error': 'invalid block num'}), 400)

        block = int(block)

    try:
        return jsonify(get_admin_fees(chain, block))
    except BadFunctionCallOutput:
        # Contract didn't exist then basically, this happens in blocks
        # before the metapool contract deployment.
        return (jsonify({'error': 'contract not deployed'}), 400)

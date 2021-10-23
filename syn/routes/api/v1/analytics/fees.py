#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from flask import Blueprint, jsonify, request

from web3.exceptions import BadFunctionCallOutput

from syn.utils.analytics.fees import get_admin_fees
from syn.utils.data import SYN_DATA
from syn.utils import verify

fees_bp = Blueprint('fees_bp', __name__)


@fees_bp.route('/admin/<chain>', methods=['GET'])
def adminfees_chain(chain: str):
    if chain not in SYN_DATA:
        return (jsonify({
            'error': 'invalid chain',
            'valids': list(SYN_DATA),
        }), 400)

    # TODO(blaze): On some RPC nodes they limit past blocks and this throws
    # an error messily here.
    block = request.args.get('block', 'latest')
    if block != 'latest':
        if not verify.isdigit(block):
            return (jsonify({'error': 'invalid block num'}), 400)

        block = int(block)

    try:
        return jsonify({'admin_fee': get_admin_fees(chain, block)})
    except BadFunctionCallOutput:
        # Contract didn't exist then basically, this happens in blocks
        # before the metapool contract deployment.
        return jsonify({'admin_fee': 0})

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
from web3 import Web3

from syn.utils.analytics.fees import get_admin_fees, get_chain_bridge_fees, get_pending_admin_fees, \
    get_chain_validator_gas_fees
from syn.utils.analytics.treasury import get_treasury_erc20_balances
from syn.routes.api.v1.analytics.volume import symbol_to_address
from syn.utils.data import SYN_DATA, cache, _forced_update
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

    block = request.args.get('block', 'latest')
    if block != 'latest':
        if not verify.isdigit(block):
            return (jsonify({'error': 'invalid block num'}), 400)

        block = int(block)

    try:
        return jsonify(get_admin_fees(chain, block, handle_decimals=True))
    except BadFunctionCallOutput:
        # Contract didn't exist then basically, this happens in blocks
        # before the metapool contract deployment.
        return (jsonify({'error': 'contract not deployed'}), 400)


@fees_bp.route('/admin/<chain>/pending', methods=['GET'])
@cache.cached(timeout=TIMEOUT, forced_update=_forced_update)
def pending_adminfees_chain(chain: str):
    chainzzz = list(SYN_DATA)
    chainzzz.remove('harmony')
    chainzzz.remove('fantom')
    chainzzz.remove('arbitrum')

    if chain not in chainzzz:
        return (jsonify({
            'error': 'invalid chain',
            'valids': chainzzz,
        }), 400)

    block = request.args.get('block', 'latest')
    if block != 'latest':
        if not verify.isdigit(block):
            return (jsonify({'error': 'invalid block num'}), 400)

        block = int(block)

    # The tokens can be found here.
    ret = get_treasury_erc20_balances(chain)
    tokens = [Web3.toChecksumAddress(x) for x in ret.keys()]

    try:
        return jsonify(
            get_pending_admin_fees(
                chain,
                block,
                tokens=tokens,  # type: ignore
                handle_decimals=True))
    except BadFunctionCallOutput:
        # Contract didn't exist then basically, this happens in blocks
        # before the metapool contract deployment.
        return (jsonify({'error': 'contract not deployed'}), 400)


@fees_bp.route('/validator/', defaults={'chain': ''}, methods=['GET'])
@fees_bp.route('/validator/<chain>', methods=['GET'])
@cache.cached(timeout=TIMEOUT, forced_update=_forced_update)
def chain_validator_gas_fees(chain: str):
    if chain not in SYN_DATA:
        return (jsonify({
            'error': 'invalid chain',
            'valids': list(SYN_DATA),
        }), 400)

    return jsonify(get_chain_validator_gas_fees(chain))


@fees_bp.route('/bridge/<chain>/', defaults={'token': ''}, methods=['GET'])
@fees_bp.route('/bridge/<chain>/<token>', methods=['GET'])
@cache.cached(timeout=TIMEOUT, forced_update=_forced_update)
def chain_bridge_fees(chain: str, token: str):
    if chain not in SYN_DATA:
        return (jsonify({
            'error': 'invalid chain',
            'valids': list(SYN_DATA),
        }), 400)
    elif token not in symbol_to_address[chain]:
        return (jsonify({
            'error': 'invalid token',
            'valids': list(symbol_to_address[chain]),
        }), 400)

    return jsonify(
        get_chain_bridge_fees(chain, symbol_to_address[chain][token]))

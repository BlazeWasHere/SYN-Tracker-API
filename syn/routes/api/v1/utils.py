#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from collections import defaultdict
from datetime import datetime

from flask import Blueprint, jsonify, request
from web3 import Web3

from syn.utils.data import LOGS_REDIS_URL, SYN_DATA, cache, TOKENS_INFO
from syn.utils.helpers import get_all_keys, date2block
from syn.utils.price import ADDRESS_TO_CGID, CUSTOM, get_price_for_address, get_historic_price_for_address

from syn.utils.explorer.data import CHAINS, CHAINS_REVERSED
from syn.utils import verify

utils_bp = Blueprint('utils_bp', __name__)


# Something a bit more internal, but useful for tracking sync status because
# we launch `update_getlogs` as a daemon now.
@utils_bp.route('/syncing', methods=['GET'])
def syncing():
    ret = get_all_keys('*MAX_BLOCK_STORED',
                       serialize=True,
                       index=0,
                       client=LOGS_REDIS_URL,
                       use_max_of_duped_keys=True)
    res = defaultdict(dict)

    for chain, v in ret.items():
        w3: Web3 = SYN_DATA[chain]['w3']
        res[chain] = {'current': v, 'blockheight': w3.eth.block_number}

    return jsonify(res)


@utils_bp.route('/date2block/<chain:chain>/<date:date>', methods=['GET'])
@cache.cached()
def chain_date_to_block(chain: str, date: datetime):
    _date = date.date()
    return jsonify({str(_date): date2block(chain, _date)})


@utils_bp.route('/chains', methods=['GET'])
def chains():
    return jsonify(CHAINS)


@utils_bp.route('/tokens', methods=['GET'])
def tokens():
    res = defaultdict(dict)

    for chain, data in TOKENS_INFO.items():
        for token, _data in data.items():
            res[chain][token] = {
                'decimals': _data['decimals'],
                'symbol': _data['symbol'],
                'name': _data['name'],
            }

            if token in CUSTOM[chain]:
                res[chain][token].update({'cgid': None})
            else:
                cgid = ADDRESS_TO_CGID[chain][token].value
                res[chain][token].update({'cgid': cgid})

    return res


@utils_bp.route('/token_price', methods=['GET'])
@cache.cached()
def token_price():
    chain_id = request.args.get('token', None)
    token = request.args.get('token', None)
    date = request.args.get('date', None)

    # validate chain id
    if not verify.isdigit(chain_id) or (chain_id := int(chain_id) not in CHAINS_REVERSED):
        return jsonify({'error': 'invalid chain id'}), 400
    chain_name = CHAINS_REVERSED[chain_id]

    # validate token address
    if token not in ADDRESS_TO_CGID[chain_name]:
        return jsonify({'error': 'token for chain not supported'}), 400

    # validate date format if entered
    if date:
        try:
            datetime.strptime(date, '%d-%m-%Y')
        except ValueError:
            return jsonify({'error': 'invalid date entered. Must be formatted as %d-%m-%Y'}), 400
        res = get_historic_price_for_address(chain=chain_name, address=token, date=date)
    else:
        res = get_price_for_address(chain=chain_name, address=token)

    return jsonify({
        'price': str(res)
    })

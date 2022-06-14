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

from syn.utils.price import (ADDRESS_TO_CGID, get_price_for_address,
                             get_historic_price_for_address, CUSTOM)
from syn.utils.data import (LOGS_REDIS_URL, SYN_DATA, cache, TOKENS_INFO,
                            symbol_to_address)
from syn.utils.helpers import get_all_keys, date2block
from syn.utils.explorer.data import CHAINS

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

            if (cgid := ADDRESS_TO_CGID[chain].get(token)):
                res[chain][token].update({'cgid': cgid.value})
            else:
                res[chain][token].update({'cgid': None})

    return res


@utils_bp.route('/price/<chain:chain>/<token>', methods=['GET'])
@cache.cached(query_string=True)
def token_price(chain: str, token: str):
    date = request.args.get('date', type=datetime.fromisoformat)
    token = token.lower()

    # Check if user supplied a symbol (e.g. SYN), if this is true then get
    # the address else fallback to `token` (which means address supplied).
    token = symbol_to_address[chain].get(token, token)

    # validate token address
    if token not in ADDRESS_TO_CGID[chain]:
        return (jsonify({'error': 'token for chain not supported'}), 400)

    if date is not None:
        res = get_historic_price_for_address(chain=chain,
                                             address=token,
                                             date=str(date))
    else:
        # get current price if no date entered
        res = get_price_for_address(chain=chain, address=token)

    return jsonify({'price': res})

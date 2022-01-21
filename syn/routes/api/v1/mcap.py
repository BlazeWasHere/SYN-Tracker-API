#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from flask import Blueprint, jsonify

from syn.routes.api.v1.circ import get_all_chains_circ_supply, \
    get_chain_circ_cupply
from syn.utils.price import CoingeckoIDS, get_price_coingecko
from syn.utils.data import cache

mcap_bp = Blueprint('mcap_bp', __name__)


@mcap_bp.route('/', methods=['GET'])
@cache.cached()
def mcap():
    return jsonify({
        'market_cap':
        get_price_coingecko(CoingeckoIDS.SYN) * get_all_chains_circ_supply()
    })


@mcap_bp.route('/<chain:chain>', methods=['GET'])
@cache.cached()
def mcap_chain(chain: str):
    ret = get_chain_circ_cupply(chain)
    return jsonify({'market_cap': get_price_coingecko(CoingeckoIDS.SYN) * ret})

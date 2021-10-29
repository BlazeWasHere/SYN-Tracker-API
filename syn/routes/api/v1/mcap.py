#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from flask import Blueprint, jsonify
import requests

from .circ import get_all_chains_circ_supply, get_chain_circ_cupply, SYN_DATA
from syn.utils.price import CoingeckoIDS, get_price_coingecko

mcap_bp = Blueprint('mcap_bp', __name__)


@mcap_bp.route('/', methods=['GET'])
def mcap():
    return jsonify({
        'market_cap':
        round(
            get_price_coingecko(CoingeckoIDS.SYN) *
            get_all_chains_circ_supply(), 2)
    })


@mcap_bp.route('/<chain>', methods=['GET'])
def mcap_chain(chain: str):
    if chain not in SYN_DATA:
        return (jsonify({
            'error': 'invalid chain',
            'valids': list(SYN_DATA),
        }), 400)

    ret = get_chain_circ_cupply(chain)

    return jsonify(
        {'market_cap': round(get_price_coingecko(CoingeckoIDS.SYN) * ret, 2)})

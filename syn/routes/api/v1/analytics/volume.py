#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Callable, Dict

from flask import Blueprint, jsonify

from syn.utils.analytics.volume import get_chain_volume
from syn.utils.data import SYN_DATA, DEFILLAMA_DATA

volume_bp = Blueprint('volume_bp', __name__)
ETH_TOKENS = ['nusd', 'syn', 'high', 'dog', 'usdt', 'usdc', 'dai']


def eth_filter_factory(
    key: str,
    address: str = DEFILLAMA_DATA['bridges']['ethereum']['metaswap']
) -> Callable[[Dict[str, str]], bool]:
    def filter(x: Dict[str, str]) -> bool:
        return x['to_address'] == address.lower() \
            and x['address'] == SYN_DATA['ethereum'][key].lower()

    return filter


@volume_bp.route('/ethereum/filter/<token>', methods=['GET'])
def volume_eth_filter(token: str):
    if token not in ETH_TOKENS:
        return (jsonify({
            'error': 'invalid token',
            'valids': ETH_TOKENS,
        }), 400)
    elif token == 'syn':
        token = 'address'

    address = DEFILLAMA_DATA['bridges']['ethereum']['metaswap']
    return jsonify(get_chain_volume(address, 'eth', eth_filter_factory(token)))

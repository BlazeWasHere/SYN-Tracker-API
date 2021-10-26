#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from flask import Blueprint, jsonify

from syn.utils.analytics.volume import get_chain_volume
from syn.utils.data import SYN_DATA, DEFILLAMA_DATA

volume_bp = Blueprint('volume_bp', __name__)
_chains = {
    'ethereum': 'eth',
    'polygon': 'polygon',
    'bsc': 'bsc',
    'avalanche': 'avalanche'
}


@volume_bp.route('/<chain>', methods=['GET'])
def volume_chain(chain: str):
    if chain not in SYN_DATA or chain not in _chains:
        _list = list(SYN_DATA)
        _list.remove('arbitrum')
        _list.remove('fantom')

        return (jsonify({
            'error': 'invalid chain',
            'valids': _list,
        }), 400)

    return jsonify({
        'volume':
        get_chain_volume(
            DEFILLAMA_DATA['bridges']['avax' if chain ==
                                      'avalanche' else chain]['metaswap'],
            _chains[chain])
    })

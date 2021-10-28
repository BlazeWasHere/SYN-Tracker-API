#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Callable, Dict, Optional

from flask import Blueprint, jsonify

from syn.utils.analytics.volume import get_chain_volume
from syn.utils.data import NULL_ADDR, SYN_DATA, DEFILLAMA_DATA

volume_bp = Blueprint('volume_bp', __name__)
_chains = {
    'ethereum': 'eth',
    'polygon': 'polygon',
    'bsc': 'bsc',
    'avalanche': 'avalanche'
}


def eth_filter_factory(
    key: str,
    address: str = DEFILLAMA_DATA['bridges']['ethereum']['metaswap']
) -> Callable[[Dict[str, str]], bool]:
    def filter(x: Dict[str, str]) -> bool:
        return (x['from_address'] == address.lower()
                or x['to_address'] == address.lower()
                ) and x['address'] == SYN_DATA['ethereum'][key].lower()

    return filter


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

    if chain != "ethereum":
        address = SYN_DATA[chain]['metapool']
    elif chain == "polygon":
        address = "0x0775632f3d2b8aa764e833c0e3db6382882d0f48"
    else:
        address = DEFILLAMA_DATA['bridges'][chain]['metaswap']

    def _filter(x: Dict[str, str]) -> bool:
        return (x['from_address'] == address.lower()
                or x['to_address'] == address.lower())

    return jsonify(
        {'volume': get_chain_volume(address, _chains[chain], _filter)})


@volume_bp.route('/ethereum/filter/nusd', methods=['GET'])
def volume_chain_nusd():
    address = DEFILLAMA_DATA['bridges']['ethereum']['metaswap']
    return jsonify({
        'volume':
        get_chain_volume(address, 'eth', eth_filter_factory('nusd'))
    })


@volume_bp.route('/ethereum/filter/high', methods=['GET'])
def volume_chain_high():
    address = DEFILLAMA_DATA['bridges']['ethereum']['metaswap']
    return jsonify({
        'volume':
        get_chain_volume(address, 'eth', eth_filter_factory('high'))
    })

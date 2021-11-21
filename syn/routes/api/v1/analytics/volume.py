#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from flask import Blueprint, jsonify

from syn.utils.analytics.volume import get_chain_volume, get_chain_metapool_volume
from syn.utils.data import SYN_DATA, cache, DEFAULT_TIMEOUT, _forced_update

volume_bp = Blueprint('volume_bp', __name__)

symbol_to_address = {
    'ethereum': {
        'syn': '0x0f2d719407fdbeff09d87557abb7232601fd9f29',
        'nusd': '0x1b84765de8b7566e4ceaf4d0fd3c5af52d3dde4f',
        'dog': '0xbaac2b4491727d78d2b78815144570b9f2fe8899',
        'weth': '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2',
        'high': '0x71ab77b7dbb4fa7e017bc15090b2163221420282',
        'frax': '0x853d955acef822db058eb8505911ed77f175b99e',
    },
    'bsc': {
        'syn': '0xa4080f1778e69467e905b8d6f72f6e441f9e9484',
        'nusd': '0x23b891e5c62e0955ae2bd185990103928ab817b3',
        'high': '0x5f4bde007dc06b867f86ebfe4802e34a1ffeed63',
        'jump': '0x130025ee738a66e691e6a7a62381cb33c6d9ae83',
        'nfd': '0x0fe9778c005a5a6115cbe12b0568a2d50b765a51',
        'dog': '0xaa88c603d142c371ea0eac8756123c5805edee03',
    },
    'polygon': {
        'syn': '0xf8f9efc0db77d8881500bb06ff5d6abc3070e695',
        'nusd': '0xb6c473756050de474286bed418b77aeac39b02af',
        'nfd': '0x0a5926027d407222f8fe20f24cb16e103f617046',
    },
    'fantom': {
        'syn': '0xe55e19fb4f2d85af758950957714292dac1e25b2',
        'nusd': '0xed2a7edd7413021d440b09d654f3b87712abab66',
        'jump': '0x78de9326792ce1d6eca0c978753c6953cdeedd73',
    },
    'arbitrum': {
        'syn': '0x080f6aed32fc474dd5717105dba5ea57268f46eb',
        'neth': '0x3ea9b0ab55f34fb188824ee288ceaefc63cf908e',
        'nusd': '0x2913e812cf0dcca30fb28e6cac3d2dcff4497688',
    },
    'avalanche': {
        'syn': '0x1f1e7c893855525b303f99bdf5c3c05be09ca251',
        'nusd': '0xcfc37a6ab183dd4aed08c204d1c2773c0b1bdf46',
        'nfd': '0xf1293574ee43950e7a8c9f1005ff097a9a713959',
    },
    'harmony': {
        'syn': '0xe55e19fb4f2d85af758950957714292dac1e25b2',
        'nusd': '0xed2a7edd7413021d440b09d654f3b87712abab66',
    },
    'boba': {
        'syn': '0xb554a55358ff0382fb21f0a478c3546d1106be8c',
        'nusd': '0x6b4712ae9797c199edd44f897ca09bc57628a1cf',
        'neth': '0x96419929d7949d6a801a6909c145c8eef6a40431',
    },
    'moonriver': {
        'syn': '0xd80d8688b02b3fd3afb81cdb124f188bb5ad0445',
        'synfrax': '0xe96ac70907fff3efee79f502c985a7a21bce407d',
    },
    'optimism': {
        'syn': '0x5a5fff6f753d7c11a56a52fe47a177a87e431655',
        'neth': '0x809dc529f07651bd43a172e8db6f4a7a0d771036',
    },
}


@volume_bp.route('/<chain>/filter/<token>/<direction>')
def chain_filter_token_direction(chain: str, token: str, direction: str):
    if chain not in SYN_DATA:
        return (jsonify({
            'error': 'invalid chain',
            'valids': list(SYN_DATA),
        }), 400)
    elif direction.upper() not in ['IN', 'OUT']:
        return (jsonify({
            'error': 'invalid direction',
            'valids': ['in', 'out'],
        }), 400)
    elif token not in symbol_to_address[chain]:
        return (jsonify({
            'error': 'invalid token',
            'valids': list(symbol_to_address[chain]),
        }), 400)

    if direction.upper() == 'OUT':
        direction = 'OUT:*'

    ret = get_chain_volume(symbol_to_address[chain][token], chain,
                           direction.upper())
    return jsonify(ret)


@volume_bp.route('/metapool/', defaults={'chain': ''}, methods=['GET'])
@volume_bp.route('/metapool/<chain>', methods=['GET'])
@cache.cached(timeout=DEFAULT_TIMEOUT, forced_update=_forced_update)
def volume_metapool(chain: str):
    valid_chains = list(SYN_DATA)
    valid_chains.remove('ethereum')
    valid_chains.remove('harmony')

    if chain not in valid_chains:
        return (jsonify({
            'error': f'invalid chain: {chain}',
            'valids': valid_chains,
        }), 400)

    metapool = SYN_DATA[chain]['pool']
    nusd = SYN_DATA[chain]['nusd']
    usdlp = SYN_DATA[chain]['usdlp']

    return jsonify(get_chain_metapool_volume(metapool, nusd, usdlp, chain))

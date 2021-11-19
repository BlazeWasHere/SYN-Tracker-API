#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Any, Callable, Dict, List

from flask import Blueprint, jsonify
from gevent.greenlet import Greenlet
from gevent.pool import Pool
import gevent

from syn.utils.analytics.volume import get_chain_volume, get_chain_metapool_volume
from syn.utils.data import BRIDGES, NULL_ADDR, SYN_DATA, cache, DEFAULT_TIMEOUT, \
    _forced_update
from syn.utils.helpers import merge_many_dicts, raise_if, \
    store_volume_dict_to_redis

pool = Pool()

volume_bp = Blueprint('volume_bp', __name__)

symbol_to_address = {
    'ethereum': {
        'syn': '0x0f2d719407fdbeff09d87557abb7232601fd9f29',
        'nusd': '0x1b84765de8b7566e4ceaf4d0fd3c5af52d3dde4f',
        'dai': '0x6b175474e89094c44da98b954eedeac495271d0f',
        'usdc': '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
        'usdt': '0xdac17f958d2ee523a2206206994597c13d831ec7',
    },
    'bsc': {
        'syn': '0xa4080f1778e69467e905b8d6f72f6e441f9e9484',
        'nusd': '0x23b891e5c62e0955ae2bd185990103928ab817b3',
        'busd': '0xe9e7cea3dedca5984780bafc599bd69add087d56',
        'usdc': '0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d',
        'usdt': '0x55d398326f99059ff775485246999027b3197955',
    },
    'polygon': {
        'syn': '0xf8f9efc0db77d8881500bb06ff5d6abc3070e695',
        'dai': '0x8f3cf7ad23cd3cadbd9735aff958023239c6a063',
        'usdc': '0x2791bca1f2de4661ed88a30c99a7a9449aa84174',
        'usdt': '0xc2132d05d31c914a87c6611c10748aeb04b58e8f',
        'nusd': '0xb6c473756050de474286bed418b77aeac39b02af',
    },
    'fantom': {
        'syn': '0xe55e19fb4f2d85af758950957714292dac1e25b2',
        'mim': '0x82f0b8b456c1a451378467398982d4834b6829c1',
        'usdc': '0x04068da6c83afcfa0e13ba15a6696662335d5b75',
        'usdt': '0x049d68029688eabf473097a2fc38ef61633a3c7a',
        'nusd': '0xed2a7edd7413021d440b09d654f3b87712abab66',
    },
    'arbitrum': {
        'syn': '0x080f6aed32fc474dd5717105dba5ea57268f46eb',
        'neth': '0x3ea9b0ab55f34fb188824ee288ceaefc63cf908e',
        'usdc': '0xff970a61a04b1ca14834a43f5de4533ebddb5cc8',
        'usdt': '0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9',
        'mim': '0xfea7a6a0b346362bf88a9e4a88416b77a57d6c2a',
        'nusd': '0x2913e812cf0dcca30fb28e6cac3d2dcff4497688',
    },
    'avalanche': {
        'syn': '0x1f1e7c893855525b303f99bdf5c3c05be09ca251',
        'dai': '0xd586e7f844cea2f87f50152665bcbc2c279d8d70',
        'usdc': '0xa7d7079b0fead91f3e65f86e8915cb59c1a4c664',
        'usdt': '0xc7198437980c041c805a1edcba50c1ce5db95118',
        'nusd': '0xcfc37a6ab183dd4aed08c204d1c2773c0b1bdf46',
    },
    'harmony': {
        'syn': '0xe55e19fb4f2d85af758950957714292dac1e25b2',
        'dai': '0xef977d2f931c1978db5f6747666fa1eacb0d0339',
        'usdc': '0x985458e523db3d53125813ed68c274899e9dfab4',
        'usdt': '0x3c2b8be99c50593081eaa2a724f0b8285f5aba8f',
        'nusd': '0xed2a7edd7413021d440b09d654f3b87712abab66',
    },
    'boba': {
        'syn': '0xb554a55358ff0382fb21f0a478c3546d1106be8c',
        'dai': '0xf74195bb8a5cf652411867c5c2c5b8c2a402be35',
        'nusd': '0x6b4712ae9797c199edd44f897ca09bc57628a1cf',
        'usdt': '0x5de1677344d3cb0d7d465c10b72a8f60699c062d',
        'usdc': '0x66a2a913e447d6b4bf33efbec43aaef87890fbbc',
    },
    'moonriver': {
        'syn': '0xd80d8688b02b3fd3afb81cdb124f188bb5ad0445',
        'synfrax': '0xe96ac70907fff3efee79f502c985a7a21bce407d',
    }
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

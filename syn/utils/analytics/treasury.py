#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from collections import defaultdict
from decimal import Decimal
from typing import Dict

from web3.types import BlockIdentifier

from syn.utils.price import get_price_coingecko, get_price_for_address
from syn.utils.data import SYN_DATA, TOKEN_DECIMALS, TREASURY
from syn.utils.analytics.fees import _chain_to_cgid
from syn.utils.explorer.data import TOKENS_IN_POOL
from syn.utils.contract import get_balance_of
from syn.utils.helpers import handle_decimals
from syn.utils.cache import timed_cache


@timed_cache(60, maxsize=50)
def get_treasury_erc20_balances(
        chain: str,
        block: BlockIdentifier = 'latest',
        include_native: bool = True) -> Dict[str, Decimal]:
    res: Dict[str, Decimal] = defaultdict(Decimal)
    w3 = SYN_DATA[chain]['w3']

    _tokens = TOKENS_IN_POOL[chain]
    _tokens.update({'syn': {0: SYN_DATA[chain]['address']}})
    if 'usdlp' in SYN_DATA[chain]:
        _tokens.update({'usdlp': {0: SYN_DATA[chain]['usdlp']}})

    if chain == 'ethereum':
        _tokens.update({
            'weth': {
                0: '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2',
            },
            'high': {
                0: '0x71ab77b7dbb4fa7e017bc15090b2163221420282',
            },
            'nusd': {
                0: '0x1b84765de8b7566e4ceaf4d0fd3c5af52d3dde4f',
            }
        })
    elif chain == 'harmony':
        _tokens.update(
            {'one': {
                0: '0xcf664087a5bb0237a0bad6742852ec6c8d69a27a',
            }})

    # TODO(blaze): thread this with gevent?
    for tokens in _tokens.values():
        for token in tokens.values():
            res[token] = get_balance_of(  # type: ignore
                w3,
                token,
                TREASURY[chain],
                TOKEN_DECIMALS[chain][token.lower()],
                block=block)

    if include_native:
        # Let's bet its 18 decimals.
        res['native'] = handle_decimals(
            w3.eth.get_balance(TREASURY[chain], block_identifier=block), 18)

    return res


def get_treasury_erc20_balances_usd(
        chain: str,
        block: BlockIdentifier = 'latest') -> Dict[str, Dict[str, Decimal]]:
    res = defaultdict(dict)
    ret = get_treasury_erc20_balances(chain, block)

    for k, v in ret.items():
        if k == 'native':
            price = get_price_coingecko(_chain_to_cgid[chain])
        else:
            price = get_price_for_address(chain, k.lower())

        res[k] = {'usd': price * v, 'amount': v}

    return res

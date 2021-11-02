#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from collections import defaultdict
from typing import Dict, cast

from syn.utils.data import TREASURY, MORALIS_APIKEY
from syn.utils.price import get_price_for_address
from syn.utils.wrappa.moralis import Moralis
from syn.utils.cache import timed_cache

moralis = Moralis(MORALIS_APIKEY)


@timed_cache(60, maxsize=50)
def get_treasury_erc20_balances(chain: str,
                                to_block: int = 0) -> Dict[str, float]:
    res = defaultdict(dict)
    ret = moralis.erc20_balances(TREASURY[chain], chain, to_block)

    if ret:
        for x in ret:
            amount = int(x['balance']) / 10**int(x['decimals'])
            price = get_price_for_address(chain, x['token_address'])
            res[x['token_address']] = {
                'amount': amount,
                'usd': amount * price,
                'symbol': x['symbol'],
            }

    return cast(Dict[str, float], res)

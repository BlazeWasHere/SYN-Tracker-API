#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Dict, List
from decimal import Decimal

from web3.types import BlockIdentifier
from web3.contract import Contract

from syn.utils.price import get_price_defillama_usd, defillama_serialize
from syn.utils.helpers import convert_amount


def get_tvl(
    chain: str,
    contract: Contract,
    block: BlockIdentifier,
    timestamp: int,
    tokens: List[str],
) -> Dict[str, Decimal]:
    # (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast)
    ret = contract.functions.getReserves().call(block_identifier=block)

    t0_reserve = convert_amount(chain, tokens[0], ret[0])
    t1_reserve = convert_amount(chain, tokens[1], ret[1])

    assert t0_reserve, f'failed to get t0 {chain=} {tokens[0]} {ret=}'
    assert t1_reserve, f'failed to get t1 {chain=} {tokens[1]} {ret=}'

    return {
        tokens[0].lower(): t0_reserve,
        tokens[1].lower(): t1_reserve,
    }


def get_tvl_usd(
    chain: str,
    contract: Contract,
    block: BlockIdentifier,
    timestamp: int,
    tokens: List[str],
) -> Decimal:
    ret = get_tvl(chain, contract, block, timestamp, tokens)
    res = Decimal()

    prices = get_price_defillama_usd([
        defillama_serialize(chain, tokens[0]),
        defillama_serialize(chain, tokens[1]),
    ], timestamp)

    for token, price in prices.items():
        for _token, liq in ret.items():
            # Cannot assume `ret.keys()` == `prices.keys()`
            if token == _token:
                res += liq * price

    return res

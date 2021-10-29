#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from enum import Enum

import requests

from .data import COINGECKO_BASE_URL
from .cache import timed_cache


class CoingeckoIDS(Enum):
    HIGH = 'highstreet'
    SYN = 'synapse-2'
    USDT = 'tether'
    USDC = 'usd-coin'
    BUSD = 'binance-usd'
    DAI = 'dai'
    ETH = 'ethereum'


CUSTOM = {
    'eth': {
        # nUSD
        '0x1b84765de8b7566e4ceaf4d0fd3c5af52d3dde4f': 1,
    },
    'bsc': {
        # nUSD
        '0x23b891e5c62e0955ae2bd185990103928ab817b3': 1,
        # USD-LP
        '0xf0b8b631145d393a767b4387d08aa09969b2dfed': 1,
        # BSC-USD
        '0x55d398326f99059ff775485246999027b3197955': 1,
        '0xdfd717f4e942931c98053d5453f803a1b52838db': 0,
    },
}

ADDRESS_TO_CGID = {
    'eth': {
        '0x71ab77b7dbb4fa7e017bc15090b2163221420282': CoingeckoIDS.HIGH,
        '0x0f2d719407fdbeff09d87557abb7232601fd9f29': CoingeckoIDS.SYN,
        '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2': CoingeckoIDS.ETH,
        '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48': CoingeckoIDS.USDC,
        '0x6b175474e89094c44da98b954eedeac495271d0f': CoingeckoIDS.DAI,
        '0xdac17f958d2ee523a2206206994597c13d831ec7': CoingeckoIDS.USDT,
    },
    'bsc': {
        '0xe9e7cea3dedca5984780bafc599bd69add087d56': CoingeckoIDS.BUSD,
        '0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d': CoingeckoIDS.USDC,
    },
}


def get_price_for_address(chain: str, address: str) -> float:
    if address in CUSTOM[chain]:
        return CUSTOM[chain][address]

    return get_price_coingecko(ADDRESS_TO_CGID[chain][address])


@timed_cache(60 * 10, maxsize=500)
def get_price_coingecko(_id: CoingeckoIDS, currency: str = "usd") -> float:
    r = requests.get(COINGECKO_BASE_URL.format(_id.value, currency))
    return r.json()[_id.value][currency]


def init() -> None:
    """Fire up the LRU cache."""
    [get_price_coingecko(x) for x in CoingeckoIDS]
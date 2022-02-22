#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import DefaultDict, Dict
from collections import defaultdict
from enum import Enum

from syn.utils.contract import get_all_tokens_in_pool
from syn.utils.data import SYN_DATA

CHAINS = {
    43114: 'avalanche',
    1666600000: 'harmony',
    42161: 'arbitrum',
    250: 'fantom',
    137: 'polygon',
    56: 'bsc',
    1: 'ethereum',
    288: 'boba',
    1285: 'moonriver',
    10: 'optimism',
    1313161554: 'aurora',
    1284: 'moonbeam',
    25: 'cronos',
    1088: 'metis',
}


class Direction(Enum):
    def __str__(self) -> str:
        return self.name

    OUT = 0
    IN = 1


EVENTS = {
    'TokenRedeemAndSwap': Direction.OUT,
    'TokenMintAndSwap': Direction.IN,
    'TokenRedeemAndRemove': Direction.OUT,
    'TokenRedeem': Direction.OUT,
    'TokenMint': Direction.IN,
    'TokenDepositAndSwap': Direction.OUT,
    'TokenWithdrawAndRemove': Direction.IN,
    'TokenDeposit': Direction.OUT,
    'TokenWithdraw': Direction.IN,
}

TOPICS = {
    # TokenRedeemAndSwap
    '0x91f25e9be0134ec851830e0e76dc71e06f9dade75a9b84e9524071dbbc319425':
    Direction.OUT,
    # TokenMintAndSwap
    '0x4f56ec39e98539920503fd54ee56ae0cbebe9eb15aa778f18de67701eeae7c65':
    Direction.IN,
    # TokenRedeemAndRemove
    '0x9a7024cde1920aa50cdde09ca396229e8c4d530d5cfdc6233590def70a94408c':
    Direction.OUT,
    # TokenRedeem
    '0xdc5bad4651c5fbe9977a696aadc65996c468cde1448dd468ec0d83bf61c4b57c':
    Direction.OUT,
    # TokenMint
    '0xbf14b9fde87f6e1c29a7e0787ad1d0d64b4648d8ae63da21524d9fd0f283dd38':
    Direction.IN,
    # TokenDepositAndSwap
    '0x79c15604b92ef54d3f61f0c40caab8857927ca3d5092367163b4562c1699eb5f':
    Direction.OUT,
    # TokenWithdrawAndRemove
    '0xc1a608d0f8122d014d03cc915a91d98cef4ebaf31ea3552320430cba05211b6d':
    Direction.IN,
    # TokenDeposit
    '0xda5273705dbef4bf1b902a131c2eac086b7e1476a8ab0cb4da08af1fe1bd8e3b':
    Direction.OUT,
    # TokenWithdraw
    '0x8b0afdc777af6946e53045a4a75212769075d30455a212ac51c9b16f9c5c9b26':
    Direction.IN,
}

TOPIC_TO_EVENT = dict(zip(TOPICS.keys(), EVENTS.keys()))

_TKS = DefaultDict[str, Dict[str, Dict[int, str]]]
#: Example schema:
#: {'arbitrum':
#:   {'neth': {0: '0x3ea9B0ab55F34Fb188824Ee288CeaEfC63cf908e',
#:             1: '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1'},
#:    'nusd': {0: '0x2913E812Cf0dcCA30FB28E6Cac3d2DCFF4497688',
#:             1: '0xFEa7a6a0B346362BF88A9e4A88416B77a57D6c2A',
#:             2: '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8',
#:             3: '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9'}}
TOKENS_IN_POOL: _TKS = defaultdict(lambda: defaultdict(dict))

for chain, v in SYN_DATA.items():
    if 'pool_contract' in v:
        ret = get_all_tokens_in_pool(chain)

        for i, token in enumerate(ret):
            TOKENS_IN_POOL[chain]['nusd'].update({i: token})

    if 'ethpool_contract' in v:
        ret = get_all_tokens_in_pool(chain, func='ethpool_contract')

        for i, token in enumerate(ret):
            TOKENS_IN_POOL[chain]['neth'].update({i: token})

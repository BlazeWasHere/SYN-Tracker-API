#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Callable, Dict, Protocol, List
from decimal import Decimal
import json
import os

from web3.types import BlockIdentifier
from web3.contract import Contract
from web3 import Web3

from syn.utils.dexes.modules import uniswapv2
from syn.utils.data import SYN_DATA

_abis_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'abis')

AVAILABLE_MODULES = [
    'uniswapv2',
]


class ModuleProto(Protocol):
    get_tvl: Callable[[str, Contract, BlockIdentifier, int, List[str]],
                      Dict[str, Decimal]]
    get_tvl_usd: Callable[[str, Contract, BlockIdentifier, int, List[str]],
                          Decimal]


class Module(object):
    def __init__(self, name: str, chain: str, address: str,
                 tokens: List[str]) -> None:
        assert name in AVAILABLE_MODULES, f'invalid module: {name!r}'
        assert chain in SYN_DATA, f'invalid chain: {chain!r}'

        with open(os.path.join(_abis_path, f'{name}.json')) as f:
            self.abi = json.loads(f.read())

        self.w3: Web3 = SYN_DATA[chain]['w3']

        self.name = name
        self.chain = chain
        self.tokens = tokens
        self.address = self.w3.toChecksumAddress(address)
        self.contract = self.w3.eth.contract(self.address, abi=self.abi)

        self._module: ModuleProto = globals()[name]

    def __repr__(self) -> str:
        return f'dexes.Module({self.name!r}, {self.chain!r}, {self.address!r})'

    def _block_timestamp(self, block: BlockIdentifier) -> int:
        ret = self.w3.eth.get_block(block)

        if timestamp := ret.get('timestamp'):
            return timestamp

        raise RuntimeError(f'failed to get timestamp: {block=} {ret=}')

    def get_tvl(self, block: BlockIdentifier = 'latest') -> Dict[str, Decimal]:
        return self._module.get_tvl(
            self.chain,
            self.contract,
            block,
            self._block_timestamp(block),
            self.tokens,
        )

    def get_tvl_usd(self, block: BlockIdentifier = 'latest') -> Decimal:
        return self._module.get_tvl_usd(
            self.chain,
            self.contract,
            block,
            self._block_timestamp(block),
            self.tokens,
        )


uniswapv2_syn_frax = Module('uniswapv2', 'ethereum',
                            '0x9fae36a18ef8ac2b43186ade5e2b07403dc742b1', [
                                '0x0f2d719407fdbeff09d87557abb7232601fd9f29',
                                '0x853d955acef822db058eb8505911ed77f175b99e',
                            ])

__all__ = ['uniswapv2_syn_frax']

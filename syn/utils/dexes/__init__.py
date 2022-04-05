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
sushiswap_syn_weth = Module('uniswapv2', 'ethereum',
                            '0x4a86c01d67965f8cb3d0aaa2c655705e64097c31', [
                                '0x0f2d719407fdbeff09d87557abb7232601fd9f29',
                                '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
                            ])
traderjoe_syn_wavax = Module('uniswapv2', 'avalanche',
                             '0x20abdc20758990b6afc90da2f2d30cd0aa3f73c6', [
                                 '0x1f1E7c893855525b303f99bDF5c3c05Be09ca251',
                                 '0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7',
                             ])
solidly_usdc_syn = Module('uniswapv2', 'fantom',
                          '0xb1b3b96cf35435b2518093acd50e02fe03a0131f', [
                              '0x04068DA6C83AFCFA0e13ba15A6696662335D5B75',
                              '0xE55e19Fb4F2D85af758950957714292DAC1e25B2',
                          ])
solidly_wftm_syn = Module('uniswapv2', 'fantom',
                          '0x8aa410d8b0cc3de48aac8eb5d928646a00e6ff04', [
                              '0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83',
                              '0xE55e19Fb4F2D85af758950957714292DAC1e25B2',
                          ])

__all__ = [
    'uniswapv2_syn_frax',
    'sushiswap_syn_weth',
    'traderjoe_syn_wavax',
    'solidly_usdc_syn',
    'solidly_wftm_syn',
]

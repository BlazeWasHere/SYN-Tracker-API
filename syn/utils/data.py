#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from web3 import Web3

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/synapse-2?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false"

TOTAL_SUPPLY_ABI = """[{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"}]"""
METAPOOL_ABI = """[{"inputs":[{"internalType":"uint8","name":"index","type":"uint8"}],"name":"getToken","outputs":[{"internalType":"contract IERC20","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"index","type":"uint256"}],"name":"getAdminBalance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]"""

SYN_DECIMALS = 18
SYN_DATA = {
    "ethereum": {
        "rpc":
        "https://eth-mainnet.alchemyapi.io/v2/0AovFRYl9L7l4YUf6nPaMrs7H2_pj_Pf",
        "address": "0x0f2D719407FdBeFF09D87557AbB7232601FD9F29",
        "metapool": "0x1116898DdA4015eD8dDefb84b6e8Bc24528Af2d8"
    },
    "avalanche": {
        "rpc": "https://api.avax.network/ext/bc/C/rpc",
        "address": "0x1f1E7c893855525b303f99bDF5c3c05Be09ca251",
    },
    "bsc": {
        "rpc": "https://bsc-dataseed.binance.org",
        "address": "0xa4080f1778e69467e905b8d6f72f6e441f9e9484",
    },
    "polygon": {
        "rpc": "https://rpc-mainnet.matic.network",
        "address": "0xf8f9efc0db77d8881500bb06ff5d6abc3070e695",
    },
    "arbitrum": {
        "rpc": "https://arb1.arbitrum.io/rpc",
        "address": "0x080f6aed32fc474dd5717105dba5ea57268f46eb",
    },
    "fantom": {
        "rpc": "https://rpc.ftm.tools",
        "address": "0xe55e19fb4f2d85af758950957714292dac1e25b2",
    }
}

# Init 'func' to append `contract` to SYN_DATA so we can call the ABI simpler later.
for key, value in SYN_DATA.items():
    w3 = Web3(Web3.HTTPProvider(value['rpc']))
    value.update({
        'contract':
        w3.eth.contract(Web3.toChecksumAddress(value['address']),
                        abi=TOTAL_SUPPLY_ABI)  # type: ignore
    })

    if value.get('metapool') is not None:
        value.update({
            'metapool_contract':
            w3.eth.contract(Web3.toChecksumAddress(value['metapool']),
                            abi=METAPOOL_ABI)  # type: ignore
        })

# Data for the adaper: https://github.com/DefiLlama/DefiLlama-Adapters/blob/main/projects/synapse/index.js
DEFILLAMA_DATA = {
    "bridges": {
        "bsc": {
            "metaswap": "0x930d001b7efb225613ac7f35911c52ac9e111fa9",
            "usd-lp": "0xf0b8b631145d393a767b4387d08aa09969b2dfed",
            "obscure": "0x14016e85a25aeb13065688cafb43044c2ef86784",
            "obscure-decimals": 18
        },
        "ethereum": {
            "metaswap": "0x2796317b0fF8538F253012862c06787Adfb8cEb6",
            "obscure": "0x8e870d67f660d95d5be530380d0ec0bd388289e1",
            "obscure-decimals": 18
        },
        "polygon": {
            "metaswap": "0x96cf323E477Ec1E17A4197Bdcc6f72Bb2502756a",
            "usd-lp": "0x128a587555d1148766ef4327172129b50ec66e5d",
            "obscure": "0x104592a158490a9228070e0a8e5343b499e125d0",
            "obscure-decimals": 18
        },
        "avax": {
            "metaswap": "0xf44938b0125a6662f9536281ad2cd6c499f22004",
            "usd-lp": "0x55904f416586b5140a0f666cf5acf320adf64846",
            "obscure": "0x4fbf0429599460D327BD5F55625E30E4fC066095",
            "obscure-decimals": 18
        },
        "fantom": {
            "metaswap": "0xaed5b25be1c3163c907a471082640450f928ddfe",
            "obscure": "0x04068da6c83afcfa0e13ba15a6696662335d5b75",
            "obscure-decimals": 6
        },
        "arbitrum": {
            "obscure": "0x82af49447d8a07e3bd95bd0d56f35241523fbab1",
            "obscure-decimals": 18
        }
    },
    "subgraphs": {
        "bsc":
        "https://api.thegraph.com/subgraphs/name/aureliusbtc/bsc-synapse-amm",
        "ethereum":
        "https://api.thegraph.com/subgraphs/name/aureliusbtc/mainnet-synapse-amm",
        "polygon":
        "https://api.thegraph.com/subgraphs/name/aureliusbtc/polygon-synapse-amm",
        "avax":
        "https://api.thegraph.com/subgraphs/name/aureliusbtc/avalanche-synapse-amm",
        "arbitrum":
        "https://api.thegraph.com/subgraphs/name/aureliusbtc/arbitrum-synapse-amm",
        "fantom":
        "https://api.thegraph.com/subgraphs/name/aureliusbtc/fantom-synapse-amm"
    },
    "unsupported": ["nUSD", "Frapped USDT", "Magic Internet Money", "nETH"]
}

MAX_UINT8 = 2**8 - 1

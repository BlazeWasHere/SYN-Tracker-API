#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import cast
import os

from web3.middleware.geth_poa import geth_poa_middleware
from apscheduler.jobstores.redis import RedisJobStore
from dotenv import load_dotenv, find_dotenv
from flask_apscheduler import APScheduler
from flask_caching import Cache
from web3 import Web3
import redis

load_dotenv(find_dotenv('.env.sample'))
# If `.env` exists, let it override the sample env file.
load_dotenv(override=True)

COINGECKO_HISTORIC_URL = "https://api.coingecko.com/api/v3/coins/{0}/history?date={1}&localization=false"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3/simple/price?ids={0}&vs_currencies={1}"

TOTAL_SUPPLY_ABI = """[{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"}]"""
BASEPOOL_ABI = """[{"inputs":[{"internalType":"uint8","name":"index","type":"uint8"}],"name":"getToken","outputs":[{"internalType":"contract IERC20","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"index","type":"uint256"}],"name":"getAdminBalance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]"""
BALANCE_ABI = """[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"}]"""

COVALENT_APIKEY = cast(str, os.getenv('COVALENT_APIKEY'))
MORALIS_APIKEY = cast(str, os.getenv('MORALIS_APIKEY'))

if MORALIS_APIKEY is None:
    raise TypeError('`MORALIS_APIKEY` is not set')
elif COVALENT_APIKEY is None:
    raise TypeError('`COVALENT_APIKEY` is not set')

if os.getenv('docker') == 'true':
    REDIS = redis.Redis(os.environ['REDIS_DOCKER_HOST'],
                        int(os.environ['REDIS_DOCKER_PORT']),
                        decode_responses=True)
    REDIS_HOST = os.environ['REDIS_DOCKER_HOST']
    REDIS_PORT = int(os.environ['REDIS_DOCKER_PORT'])
else:
    REDIS = redis.Redis(os.environ['REDIS_HOST'],
                        int(os.environ['REDIS_PORT']),
                        decode_responses=True)
    REDIS_HOST = os.environ['REDIS_HOST']
    REDIS_PORT = int(os.environ['REDIS_PORT'])

_POPULATE_CACHE = os.getenv('POPULATE_CACHE')
if _POPULATE_CACHE is not None:
    POPULATE_CACHE = _POPULATE_CACHE.lower() == 'true'
else:
    POPULATE_CACHE = False

if POPULATE_CACHE:
    print('`POPULATE_CACHE` set to true, disable this during deployment.')

NULL_ADDR = '0x0000000000000000000000000000000000000000'

CACHE_CONFIG = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_REDIS_DB': 2,
    'CACHE_REDIS_HOST': REDIS_HOST,
    'CACHE_REDIS_PORT': REDIS_PORT
}
# 1 Hour.
DEFAULT_TIMEOUT = 60 * 60

cache = Cache(config=CACHE_CONFIG)

SCHEDULER_CONFIG = {
    'SCHEDULAR_JOBSTORES': {
        'default': RedisJobStore(db=1, host=REDIS_HOST, port=REDIS_PORT)
    },
    'SCHEDULER_API_ENABLED': True,
}

schedular = APScheduler()

CACHE_FORCED_UPDATE = POPULATE_CACHE
_forced_update = lambda: CACHE_FORCED_UPDATE

SYN_DECIMALS = 18
SYN_DATA = {
    "ethereum": {
        "rpc": os.getenv('ETH_RPC'),
        "address": "0x0f2D719407FdBeFF09D87557AbB7232601FD9F29",
        "basepool": "0x1116898DdA4015eD8dDefb84b6e8Bc24528Af2d8",
        "nusd": "0x1b84765de8b7566e4ceaf4d0fd3c5af52d3dde4f",
        "high": "0x71ab77b7dbb4fa7e017bc15090b2163221420282",
        "dog": "0xbaac2b4491727d78d2b78815144570b9f2fe8899",
        "usdt": "0xdac17f958d2ee523a2206206994597c13d831ec7",
        "usdc": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        "dai": "0x6b175474e89094c44da98b954eedeac495271d0f",
    },
    "avalanche": {
        "rpc": os.getenv('AVAX_RPC'),
        "address": "0x1f1E7c893855525b303f99bDF5c3c05Be09ca251",
        "basepool": "0xE55e19Fb4F2D85af758950957714292DAC1e25B2",
        "metapool": "0xF44938b0125A6662f9536281aD2CD6c499F22004",
    },
    "bsc": {
        "rpc": os.getenv('BSC_RPC'),
        "address": "0xa4080f1778e69467e905b8d6f72f6e441f9e9484",
        "basepool": "0x938aFAFB36E8B1AB3347427eb44537f543475cF9",
        "metapool": "0x930d001b7efb225613ac7f35911c52ac9e111fa9",
        "nusd": "0x23b891e5c62e0955ae2bd185990103928ab817b3",
        "busd": "0xe9e7cea3dedca5984780bafc599bd69add087d56",
        "usdc": "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d",
        "usdt": "0x55d398326f99059ff775485246999027b3197955",
        "dog": "0xaa88c603d142c371ea0eac8756123c5805edee03",
        "high": "0x5f4bde007dc06b867f86ebfe4802e34a1ffeed63",
    },
    "polygon": {
        "rpc": os.getenv('POLYGON_RPC'),
        "address": "0xf8f9efc0db77d8881500bb06ff5d6abc3070e695",
        "basepool": "0x3f52E42783064bEba9C1CFcD2E130D156264ca77",
        "metapool": "0x96cf323E477Ec1E17A4197Bdcc6f72Bb2502756a",
        "nusd": "0xb6c473756050de474286bed418b77aeac39b02af",
    },
    "arbitrum": {
        "rpc": os.getenv('ARB_RPC'),
        "address": "0x080f6aed32fc474dd5717105dba5ea57268f46eb",
        "basepool": "0xbafc462d00993ffcd3417abbc2eb15a342123fda",
        "metapool": "0x84cd82204c07c67dF1C2C372d8Fd11B3266F76a3",
    },
    "fantom": {
        "rpc": os.getenv('FTM_RPC'),
        "address": "0xe55e19fb4f2d85af758950957714292dac1e25b2",
        "basepool": "0x080F6AEd32Fc474DD5717105Dba5ea57268F46eb",
        "metapool": "0x1f6A0656Ff5061930076bf0386b02091e0839F9f",
    }
}

TREASURY = {
    'eth': '0x67F60b0891EBD842Ebe55E4CCcA1098d7Aac1A55',
    'bsc': '0x0056580B0E8136c482b03760295F912279170D46',
    'polygon': '0xBdD38B2eaae34C9FCe187909e81e75CBec0dAA7A',
    'avalanche': '0xd7aDA77aa0f82E6B3CF5bF9208b0E5E1826CD79C',
    'arbitrum': '0x940279D22EB27415F2b0A0Ee6287749b5B19F43D',
    'fantom': '0x224002428cF0BA45590e0022DF4b06653058F22F',
}

# Init 'func' to append `contract` to SYN_DATA so we can call the ABI simpler later.
for key, value in SYN_DATA.items():
    w3 = Web3(Web3.HTTPProvider(value['rpc']))
    assert w3.isConnected()

    if key != 'ethereum':
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    value.update({
        'contract':
        w3.eth.contract(Web3.toChecksumAddress(value['address']),
                        abi=TOTAL_SUPPLY_ABI)  # type: ignore
    })

    value.update({
        'basepool_contract':
        w3.eth.contract(Web3.toChecksumAddress(value['basepool']),
                        abi=BASEPOOL_ABI)  # type: ignore
    })

    if value.get('metapool') is not None:
        value.update({
            'metapool_contract':
            w3.eth.contract(Web3.toChecksumAddress(value['metapool']),
                            abi=BASEPOOL_ABI)  # type: ignore
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

TOKEN_DECIMALS = {
    'eth': {
        '0x71ab77b7dbb4fa7e017bc15090b2163221420282': 18,
        '0x0f2d719407fdbeff09d87557abb7232601fd9f29': 18,
        '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2': 18,
        '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48': 6,
        '0x6b175474e89094c44da98b954eedeac495271d0f': 18,
        '0xdac17f958d2ee523a2206206994597c13d831ec7': 6,
        '0x1b84765de8b7566e4ceaf4d0fd3c5af52d3dde4f': 18,
        '0xbaac2b4491727d78d2b78815144570b9f2fe8899': 18,
    },
    'bsc': {
        '0x23b891e5c62e0955ae2bd185990103928ab817b3': 18,
        '0xf0b8b631145d393a767b4387d08aa09969b2dfed': 18,
        '0xe9e7cea3dedca5984780bafc599bd69add087d56': 18,
        '0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d': 18,
        '0xaa88c603d142c371ea0eac8756123c5805edee03': 18,
    },
    'polygon': {
        '0xf8f9efc0db77d8881500bb06ff5d6abc3070e695': 18,
        '0x8f3cf7ad23cd3cadbd9735aff958023239c6a063': 18,
        '0x2791bca1f2de4661ed88a30c99a7a9449aa84174': 6,
        '0xc2132d05d31c914a87c6611c10748aeb04b58e8f': 18,
    },
}

BRIDGES = {
    'bsc': [
        # Bridge
        '0xd123f70ae324d34a9e76b67a27bf77593ba8749f',
        # Bridge Zap
        '0x612f3a0226463599ccbcabff89623904ef38bcb9',
        # Meta Bridge Zap
        '0x8027a7fa5753c8873e130f1205da9fb8691726ab',
    ],
    'polygon': [
        # Bridge
        '0x8f5bbb2bb8c2ee94639e55d5f41de9b4839c1280',
        # Bridge Zap
        '0xff0047e2156b2d62055a77fe9abbd01baa11d54a',
        # Meta Bridge Zap
        '0x0775632f3d2b8aa764e833c0e3db6382882d0f48',
    ],
}

MAX_UINT8 = 2**8 - 1

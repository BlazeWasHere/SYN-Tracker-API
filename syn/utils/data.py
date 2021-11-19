#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import cast
import json
import os

from web3.middleware.filter import local_filter_middleware
from apscheduler.schedulers.gevent import GeventScheduler
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
BASEPOOL_ABI = """[{"inputs":[{"internalType":"uint8","name":"index","type":"uint8"}],"name":"getToken","outputs":[{"internalType":"contract IERC20","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"index","type":"uint256"}],"name":"getAdminBalance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getVirtualPrice","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]"""

_abis_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'explorer', 'abis')
with open(os.path.join(_abis_path, 'bridge.json')) as f:
    BRIDGE_ABI = json.load(f)['abi']
with open(os.path.join(_abis_path, 'oldBridge.json')) as f:
    OLDBRIDGE_ABI = json.load(f)['abi']
with open(os.path.join(_abis_path, 'olderBridge.json')) as f:
    OLDERBRIDGE_ABI = json.load(f)['abi']

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

# We use this for processes to interact w/ eachother.
MESSAGE_QUEUE_REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/3'
# We use this for storing eth_GetLogs and stuff related to that.
LOGS_REDIS_URL = redis.Redis(REDIS_HOST,
                             REDIS_PORT,
                             db=4,
                             decode_responses=True)

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
    'SCHEDULER_JOBSTORES': {
        'default': RedisJobStore(db=1, host=REDIS_HOST, port=REDIS_PORT)
    }
}

schedular = APScheduler(scheduler=GeventScheduler())

CACHE_FORCED_UPDATE = POPULATE_CACHE
_forced_update = lambda: CACHE_FORCED_UPDATE

SYN_DECIMALS = 18
SYN_DATA = {
    "ethereum": {
        "rpc": os.getenv('ETH_RPC'),
        "address": "0x0f2D719407FdBeFF09D87557AbB7232601FD9F29",
        "pool": "0x1116898DdA4015eD8dDefb84b6e8Bc24528Af2d8",
        "nusd": "0x1b84765de8b7566e4ceaf4d0fd3c5af52d3dde4f",
        "high": "0x71ab77b7dbb4fa7e017bc15090b2163221420282",
        "dog": "0xbaac2b4491727d78d2b78815144570b9f2fe8899",
        "usdt": "0xdac17f958d2ee523a2206206994597c13d831ec7",
        "usdc": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        "dai": "0x6b175474e89094c44da98b954eedeac495271d0f",
        "bridge": "0x2796317b0ff8538f253012862c06787adfb8ceb6",
    },
    "avalanche": {
        "rpc": os.getenv('AVAX_RPC'),
        "address": "0x1f1E7c893855525b303f99bDF5c3c05Be09ca251",
        "pool": "0xed2a7edd7413021d440b09d654f3b87712abab66",
        "nusd": "0xcfc37a6ab183dd4aed08c204d1c2773c0b1bdf46",
        "usdlp": "0x55904f416586b5140a0f666cf5acf320adf64846",
        "bridge": "0xc05e61d0e7a63d27546389b7ad62fdff5a91aace",
    },
    "bsc": {
        "rpc": os.getenv('BSC_RPC'),
        "address": "0xa4080f1778e69467e905b8d6f72f6e441f9e9484",
        "pool": "0x28ec0b36f0819ecb5005cab836f4ed5a2eca4d13",
        "nusd": "0x23b891e5c62e0955ae2bd185990103928ab817b3",
        "usdlp": "0xf0b8b631145d393a767b4387d08aa09969b2dfed",
        "busd": "0xe9e7cea3dedca5984780bafc599bd69add087d56",
        "usdc": "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d",
        "usdt": "0x55d398326f99059ff775485246999027b3197955",
        "dog": "0xaa88c603d142c371ea0eac8756123c5805edee03",
        "high": "0x5f4bde007dc06b867f86ebfe4802e34a1ffeed63",
        "bridge": "0xd123f70ae324d34a9e76b67a27bf77593ba8749f",
    },
    "polygon": {
        "rpc": os.getenv('POLYGON_RPC'),
        "address": "0xf8f9efc0db77d8881500bb06ff5d6abc3070e695",
        "pool": "0x85fcd7dd0a1e1a9fcd5fd886ed522de8221c3ee5",
        "nusd": "0xb6c473756050de474286bed418b77aeac39b02af",
        "usdlp": "0x128a587555d1148766ef4327172129b50ec66e5d",
        "bridge": "0x8f5bbb2bb8c2ee94639e55d5f41de9b4839c1280",
    },
    "arbitrum": {
        "rpc": os.getenv('ARB_RPC'),
        "address": "0x080f6aed32fc474dd5717105dba5ea57268f46eb",
        "pool": "0x0db3fe3b770c95a0b99d1ed6f2627933466c0dd8",
        "nusd": "0x2913e812cf0dcca30fb28e6cac3d2dcff4497688",
        "usdlp": "0xe264cb5a941f98a391b9d5244378edf79bf5c19e",
        "bridge": "0x6f4e8eba4d337f874ab57478acc2cb5bacdc19c9",
    },
    "fantom": {
        "rpc": os.getenv('FTM_RPC'),
        "address": "0xe55e19fb4f2d85af758950957714292dac1e25b2",
        "pool": "0x2913e812cf0dcca30fb28e6cac3d2dcff4497688",
        "nusd": "0xed2a7edd7413021d440b09d654f3b87712abab66",
        "usdlp": "0x43cf58380e69594fa2a5682de484ae00edd83e94",
        "bridge": "0xaf41a65f786339e7911f4acdad6bd49426f2dc6b",
    },
    "harmony": {
        "rpc": os.getenv('HARMONY_RPC'),
        'address': '0xE55e19Fb4F2D85af758950957714292DAC1e25B2',
        "pool": "0x3ea9b0ab55f34fb188824ee288ceaefc63cf908e",
        "bridge": "0xaf41a65f786339e7911f4acdad6bd49426f2dc6b",
    },
    "boba": {
        "rpc": os.getenv('BOBA_RPC'),
        "address": '0xb554A55358fF0382Fb21F0a478C3546d1106Be8c',
        "pool": "0x75ff037256b36f15919369ac58695550be72fead",
        "bridge": "0x432036208d2717394d2614d6697c46df3ed69540",
    },
    "moonriver": {
        "rpc": os.getenv('MOVR_RPC'),
        "address": "0xd80d8688b02b3fd3afb81cdb124f188bb5ad0445",
        "bridge": "0xaed5b25be1c3163c907a471082640450f928ddfe",
    },
}

TREASURY = {
    'ethereum': '0x67F60b0891EBD842Ebe55E4CCcA1098d7Aac1A55',
    'bsc': '0x0056580B0E8136c482b03760295F912279170D46',
    'polygon': '0xBdD38B2eaae34C9FCe187909e81e75CBec0dAA7A',
    'avalanche': '0xd7aDA77aa0f82E6B3CF5bF9208b0E5E1826CD79C',
    'arbitrum': '0x940279D22EB27415F2b0A0Ee6287749b5B19F43D',
    'fantom': '0x224002428cF0BA45590e0022DF4b06653058F22F',
    'boba': '0xbb227Fcf45F9Dc5deF87208C534EAB1006d8Cc8d',
    'moonriver': '0x4bA30618fDcb184eC01a9B3CAe258CFc5786E70E',
}

# Init 'func' to append `contract` to SYN_DATA so we can call the ABI simpler later.
for key, value in SYN_DATA.items():
    w3 = Web3(Web3.HTTPProvider(value['rpc']))
    print(f'Checking: {key}')
    assert w3.isConnected()

    if key != 'ethereum':
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    w3.middleware_onion.add(local_filter_middleware)

    value.update({
        'contract':
        w3.eth.contract(Web3.toChecksumAddress(value['address']),
                        abi=TOTAL_SUPPLY_ABI),
        'w3':
        w3,
    })

    if value.get('pool') is not None:
        value.update({
            'pool_contract':
            w3.eth.contract(Web3.toChecksumAddress(value['pool']),
                            abi=BASEPOOL_ABI)
        })

    if value.get('bridge') is not None:
        value.update({
            'bridge_contract':
            w3.eth.contract(Web3.toChecksumAddress(value['bridge']),
                            abi=BRIDGE_ABI)
        })
print(f'All chains are connected!')

TOKEN_DECIMALS = {
    'ethereum': {
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
        '0x55d398326f99059ff775485246999027b3197955': 18,
        '0x5f4bde007dc06b867f86ebfe4802e34a1ffeed63': 18,
        '0xa4080f1778e69467e905b8d6f72f6e441f9e9484': 18,
    },
    'polygon': {
        '0xf8f9efc0db77d8881500bb06ff5d6abc3070e695': 18,
        '0x8f3cf7ad23cd3cadbd9735aff958023239c6a063': 18,
        '0x2791bca1f2de4661ed88a30c99a7a9449aa84174': 6,
        '0xc2132d05d31c914a87c6611c10748aeb04b58e8f': 6,
        '0xb6c473756050de474286bed418b77aeac39b02af': 18,
        '0x128a587555d1148766ef4327172129b50ec66e5d': 18,
    },
    'avalanche': {
        '0xd586e7f844cea2f87f50152665bcbc2c279d8d70': 18,
        '0xa7d7079b0fead91f3e65f86e8915cb59c1a4c664': 6,
        '0xc7198437980c041c805a1edcba50c1ce5db95118': 6,
        '0xcfc37a6ab183dd4aed08c204d1c2773c0b1bdf46': 18,
        '0x55904f416586b5140a0f666cf5acf320adf64846': 18,
        '0x1f1e7c893855525b303f99bdf5c3c05be09ca251': 18,
    },
    'arbitrum': {
        '0xda10009cbd5d07dd0cecc66161fc93d7c9000da1': 18,
        '0x080f6aed32fc474dd5717105dba5ea57268f46eb': 18,
        '0xff970a61a04b1ca14834a43f5de4533ebddb5cc8': 6,
        '0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9': 6,
        '0x2913e812cf0dcca30fb28e6cac3d2dcff4497688': 18,
        '0xe264cb5a941f98a391b9d5244378edf79bf5c19e': 18,
        '0xfea7a6a0b346362bf88a9e4a88416b77a57d6c2a': 18,
        '0x3ea9b0ab55f34fb188824ee288ceaefc63cf908e': 18,
    },
    'fantom': {
        '0x04068da6c83afcfa0e13ba15a6696662335d5b75': 6,
        '0x049d68029688eabf473097a2fc38ef61633a3c7a': 6,
        '0x43cf58380e69594fa2a5682de484ae00edd83e94': 18,
        '0x82f0b8b456c1a451378467398982d4834b6829c1': 18,
        '0xed2a7edd7413021d440b09d654f3b87712abab66': 18,
        '0xe55e19fb4f2d85af758950957714292dac1e25b2': 18,
    },
    'harmony': {
        '0xe55e19fb4f2d85af758950957714292dac1e25b2': 18,
        '0xef977d2f931c1978db5f6747666fa1eacb0d0339': 18,
        '0x985458e523db3d53125813ed68c274899e9dfab4': 6,
        '0x3c2b8be99c50593081eaa2a724f0b8285f5aba8f': 6,
        '0xed2a7edd7413021d440b09d654f3b87712abab66': 18,
    },
    'boba': {
        '0x66a2a913e447d6b4bf33efbec43aaef87890fbbc': 6,
        '0xb554a55358ff0382fb21f0a478c3546d1106be8c': 18,
        '0x5de1677344d3cb0d7d465c10b72a8f60699c062d': 6,
        '0xdeaddeaddeaddeaddeaddeaddeaddeaddead0000': 18,
        '0x96419929d7949d6a801a6909c145c8eef6a40431': 18,
        '0x6b4712ae9797c199edd44f897ca09bc57628a1cf': 18,
        '0xf74195bb8a5cf652411867c5c2c5b8c2a402be35': 18,
    },
    'moonriver': {
        '0xd80d8688b02b3fd3afb81cdb124f188bb5ad0445': 18,
        '0xe96ac70907fff3efee79f502c985a7a21bce407d': 18,
        '0x1a93b23281cc1cde4c4741353f3064709a16197d': 18,
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
    'ethereum': [
        # Bridge
        '0x2796317b0ff8538f253012862c06787adfb8ceb6',
    ],
}

MAX_UINT8 = 2**8 - 1

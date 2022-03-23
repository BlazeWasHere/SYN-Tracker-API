#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Dict, List, TypedDict, cast
from collections import defaultdict
import json
import os

from web3.middleware.filter import local_filter_middleware
from apscheduler.schedulers.gevent import GeventScheduler
from web3.middleware.geth_poa import geth_poa_middleware
from apscheduler.jobstores.redis import RedisJobStore
from dotenv import load_dotenv, find_dotenv
from flask_apscheduler import APScheduler
from gevent.greenlet import Greenlet
from web3.contract import Contract
from gevent.pool import Pool
from web3 import Web3
import gevent
import redis

from syn.patches.cache import PatchedCache

load_dotenv(find_dotenv('.env.sample'))
# If `.env` exists, let it override the sample env file.
load_dotenv(override=True)

COINGECKO_HISTORIC_URL = "https://api.coingecko.com/api/v3/coins/{0}/history?date={1}&localization=false"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3/simple/price?ids={0}&vs_currencies={1}"

BRIDGE_CONFIG_ABI = """[{"inputs":[{"internalType":"address","name":"tokenAddress","type":"address"},{"internalType":"uint256","name":"chainID","type":"uint256"}],"name":"getToken","outputs":[{"components":[{"internalType":"uint256","name":"chainId","type":"uint256"},{"internalType":"address","name":"tokenAddress","type":"address"},{"internalType":"uint8","name":"tokenDecimals","type":"uint8"},{"internalType":"uint256","name":"maxSwap","type":"uint256"},{"internalType":"uint256","name":"minSwap","type":"uint256"},{"internalType":"uint256","name":"swapFee","type":"uint256"},{"internalType":"uint256","name":"maxSwapFee","type":"uint256"},{"internalType":"uint256","name":"minSwapFee","type":"uint256"},{"internalType":"bool","name":"hasUnderlying","type":"bool"},{"internalType":"bool","name":"isUnderlying","type":"bool"}],"internalType":"struct BridgeConfig.Token","name":"token","type":"tuple"}],"stateMutability":"view","type":"function"}]"""
MINICHEF_ABI = """[{"inputs":[],"name":"synapsePerSecond","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]"""
TOTAL_SUPPLY_ABI = """[{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"}]"""
BASEPOOL_ABI = """[{"inputs":[{"internalType":"uint8","name":"index","type":"uint8"}],"name":"getToken","outputs":[{"internalType":"contract IERC20","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"index","type":"uint256"}],"name":"getAdminBalance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getVirtualPrice","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]"""
ERC20_BARE_ABI = """[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"}]"""

_abis_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'explorer', 'abis')
with open(os.path.join(_abis_path, 'bridge.json')) as f:
    BRIDGE_ABI = json.load(f)['abi']
with open(os.path.join(_abis_path, 'pool.json')) as f:
    POOL_ABI = json.load(f)['abi']

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
MESSAGE_QUEUE_REDIS = redis.Redis.from_url(MESSAGE_QUEUE_REDIS_URL,
                                           decode_responses=True)
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

cache = PatchedCache(config=CACHE_CONFIG)

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
        "minichef": "0xd10eF2A513cEE0Db54E959eF16cAc711470B62cF",
    },
    "avalanche": {
        "rpc": os.getenv('AVAX_RPC'),
        "address": "0x1f1E7c893855525b303f99bDF5c3c05Be09ca251",
        "pool": "0xed2a7edd7413021d440b09d654f3b87712abab66",
        "nusd": "0xcfc37a6ab183dd4aed08c204d1c2773c0b1bdf46",
        "usdlp": "0x55904f416586b5140a0f666cf5acf320adf64846",
        "bridge": "0xc05e61d0e7a63d27546389b7ad62fdff5a91aace",
        "minichef": "0x3a01521F8E7F012eB37eAAf1cb9490a5d9e18249",
        "ethpool": "0x77a7e60555bC18B4Be44C181b2575eee46212d44",
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
        "minichef": "0x8F5BBB2BB8c2Ee94639E55d5F41de9b4839C1280",
    },
    "polygon": {
        "rpc": os.getenv('POLYGON_RPC'),
        "address": "0xf8f9efc0db77d8881500bb06ff5d6abc3070e695",
        "pool": "0x85fcd7dd0a1e1a9fcd5fd886ed522de8221c3ee5",
        "nusd": "0xb6c473756050de474286bed418b77aeac39b02af",
        "usdlp": "0x128a587555d1148766ef4327172129b50ec66e5d",
        "bridge": "0x8f5bbb2bb8c2ee94639e55d5f41de9b4839c1280",
        "minichef": "0x7875Af1a6878bdA1C129a4e2356A3fD040418Be5",
    },
    "arbitrum": {
        "rpc": os.getenv('ARB_RPC'),
        "address": "0x080f6aed32fc474dd5717105dba5ea57268f46eb",
        "pool": "0x0db3fe3b770c95a0b99d1ed6f2627933466c0dd8",
        "nusd": "0x2913e812cf0dcca30fb28e6cac3d2dcff4497688",
        "usdlp": "0xe264cb5a941f98a391b9d5244378edf79bf5c19e",
        "bridge": "0x6f4e8eba4d337f874ab57478acc2cb5bacdc19c9",
        "ethpool": "0xa067668661c84476afcdc6fa5d758c4c01c34352",
        "minichef": "0x73186f2Cf2493f20836b17b21ae79fc12934E207",
        "3pool": "0x9dd329f5411466d9e0c488ff72519ca9fef0cb40",
    },
    "fantom": {
        "rpc": os.getenv('FTM_RPC'),
        "address": "0xe55e19fb4f2d85af758950957714292dac1e25b2",
        "pool": "0x2913e812cf0dcca30fb28e6cac3d2dcff4497688",
        "nusd": "0xed2a7edd7413021d440b09d654f3b87712abab66",
        "usdlp": "0x43cf58380e69594fa2a5682de484ae00edd83e94",
        "bridge": "0xaf41a65f786339e7911f4acdad6bd49426f2dc6b",
        "minichef": "0xaeD5b25BE1c3163c907a471082640450F928DDFE",
        "ethpool": "0x8d9ba570d6cb60c7e3e0f31343efe75ab8e65fb1",
        "3pool": "0x85662fd123280827e11c59973ac9fcbe838dc3b4",
    },
    "harmony": {
        "rpc": os.getenv('HARMONY_RPC'),
        'address': '0xE55e19Fb4F2D85af758950957714292DAC1e25B2',
        "pool": "0x3ea9b0ab55f34fb188824ee288ceaefc63cf908e",
        "bridge": "0xaf41a65f786339e7911f4acdad6bd49426f2dc6b",
        "minichef": "0xaeD5b25BE1c3163c907a471082640450F928DDFE",
    },
    "boba": {
        "rpc": os.getenv('BOBA_RPC'),
        "address": '0xb554A55358fF0382Fb21F0a478C3546d1106Be8c',
        "pool": "0x75ff037256b36f15919369ac58695550be72fead",
        "bridge": "0x432036208d2717394d2614d6697c46df3ed69540",
        "ethpool": "0x753bb855c8fe814233d26bb23af61cb3d2022be5",
        "minichef": "0xd5609cD0e1675331E4Fb1d43207C8d9D83AAb17C",
    },
    "moonriver": {
        "rpc": os.getenv('MOVR_RPC'),
        "address": "0xd80d8688b02b3fd3afb81cdb124f188bb5ad0445",
        "bridge": "0xaed5b25be1c3163c907a471082640450f928ddfe",
        "minichef": "0x432036208d2717394d2614d6697c46DF3Ed69540",
    },
    "optimism": {
        "rpc": os.getenv('OPTIMISM_RPC'),
        "address": "0x5a5fff6f753d7c11a56a52fe47a177a87e431655",
        "bridge": "0xaf41a65f786339e7911f4acdad6bd49426f2dc6b",
        "ethpool": "0xe27bff97ce92c3e1ff7aa9f86781fdd6d48f5ee9",
        "minichef": "0xe8c610fcb63A4974F02Da52f0B4523937012Aaa0",
    },
    "aurora": {
        "rpc": os.getenv('AURORA_RPC'),
        "address": "0xd80d8688b02b3fd3afb81cdb124f188bb5ad0445",
        "bridge": "0xaed5b25be1c3163c907a471082640450f928ddfe",
        "pool": "0xcef6c2e20898c2604886b888552ca6ccf66933b0",
        "minichef": "0x809dc529f07651bd43a172e8db6f4a7a0d771036",
    },
    "moonbeam": {
        "rpc": os.getenv('MOONBEAM_RPC'),
        "address": "0xf44938b0125a6662f9536281ad2cd6c499f22004",
        'bridge': '0x84a420459cd31c3c34583f67e0f0fb191067d32f',
        "minichef": "0xd5609cd0e1675331e4fb1d43207c8d9d83aab17c",
    },
    "cronos": {
        "rpc": os.getenv('CRONOS_RPC'),
        "address": "0xfd0f80899983b8d46152aa1717d76cba71a31616",
        "bridge": "0xe27bff97ce92c3e1ff7aa9f86781fdd6d48f5ee9",
        "minichef": "0xa9e90579eb086bcda910dd94041ffe041fb4ac89",
    },
    "metis": {
        "rpc": os.getenv('METIS_RPC'),
        "address": "0x67c10c397dd0ba417329543c1a40eb48aaa7cd00",
        "bridge": "0x06fea8513ff03a0d3f61324da709d4cf06f42a5c",
        "minichef": "0xab0d8fc46249daacd5cb36c5f0bc4f0daf34ebf5",
        "pool": "0x555982d2e211745b96736665e19d9308b615f78e",
        "ethpool": "0x09fec30669d63a13c666d2129230dd5588e2e240",
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
    'optimism': '0x2431CBdc0792F5485c4cb0a9bEf06C4f21541D52',
    'harmony': '0x0172e7190Bbc0C2Aa98E4d1281d41D0c07178605',
    'aurora': '0xbb227Fcf45F9Dc5deF87208C534EAB1006d8Cc8d',
    'moonbeam': '0xbb227Fcf45F9Dc5deF87208C534EAB1006d8Cc8d',
    'cronos': '0x7f91f3111b2009eC7c079Be213570330a37e8aeC',
    'metis': '0xEAEC50eBe1c2A981ED8be02C36b0863Fae322975',
}

# Init 'func' to append `contract` to SYN_DATA so we can call the ABI simpler later.
for key, value in SYN_DATA.items():
    w3 = Web3(Web3.HTTPProvider(value['rpc']))
    assert w3.isConnected(), key

    if key != 'ethereum':
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    w3.middleware_onion.add(local_filter_middleware)
    print(key)
    try:
        print(w3.eth.syncing)
    except Exception as e:
        print(e)

    value.update({
        'contract':
        w3.eth.contract(Web3.toChecksumAddress(value['address']),
                        abi=TOTAL_SUPPLY_ABI),
        'w3':
        w3,
        'minichef_contract':
        w3.eth.contract(Web3.toChecksumAddress(value['minichef']),
                        abi=MINICHEF_ABI)
    })

    if value.get('pool') is not None:
        value.update({
            'pool_contract':
            w3.eth.contract(Web3.toChecksumAddress(value['pool']),
                            abi=BASEPOOL_ABI)
        })

    if value.get('ethpool') is not None:
        value.update({
            'ethpool_contract':
            w3.eth.contract(Web3.toChecksumAddress(value['ethpool']),
                            abi=BASEPOOL_ABI)
        })

    if value.get('bridge') is not None:
        value.update({
            'bridge_contract':
            w3.eth.contract(Web3.toChecksumAddress(value['bridge']),
                            abi=BRIDGE_ABI)
        })

    if value.get('3pool') is not None:
        value.update({
            '3pool_contract':
            w3.eth.contract(Web3.toChecksumAddress(value['3pool']),
                            abi=BASEPOOL_ABI)
        })

# On mainnet only.
BRIDGE_CONFIG = cast(Web3, SYN_DATA['ethereum']['w3']).eth.contract(
    Web3.toChecksumAddress('0x7fd806049608b7d04076b8187dd773343e0589e6'),
    abi=BRIDGE_CONFIG_ABI)

TOKENS = {
    'ethereum': [
        '0x71ab77b7dbb4fa7e017bc15090b2163221420282',  # HIGH
        '0x0f2d719407fdbeff09d87557abb7232601fd9f29',  # SYN
        '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2',  # WETH
        '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',  # USDC
        '0x6b175474e89094c44da98b954eedeac495271d0f',  # DAI
        '0xdac17f958d2ee523a2206206994597c13d831ec7',  # USDT
        '0x1b84765de8b7566e4ceaf4d0fd3c5af52d3dde4f',  # nUSD
        '0xbaac2b4491727d78d2b78815144570b9f2fe8899',  # DOG
        '0x853d955acef822db058eb8505911ed77f175b99e',  # FRAX
        '0xca76543cf381ebbb277be79574059e32108e3e65',  # wsOHM
        '0x0ab87046fbb341d058f17cbc4c1133f25a20a52f',  # gOHM
        '0x98585dfc8d9e7d48f0b1ae47ce33332cf4237d96',  # NEWO
        '0x73968b9a57c6e53d41345fd57a6e6ae27d6cdb2f',  # SDT
        '0x02b5453d92b730f29a86a0d5ef6e930c4cf8860b',  # USDB
    ],
    'bsc': [
        '0x23b891e5c62e0955ae2bd185990103928ab817b3',  # nUSD
        '0xf0b8b631145d393a767b4387d08aa09969b2dfed',  # USD-LP
        '0xe9e7cea3dedca5984780bafc599bd69add087d56',  # BUSD
        '0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d',  # USDC
        '0xaa88c603d142c371ea0eac8756123c5805edee03',  # DOG
        '0x55d398326f99059ff775485246999027b3197955',  # USDT
        '0x5f4bde007dc06b867f86ebfe4802e34a1ffeed63',  # HIGH
        '0xa4080f1778e69467e905b8d6f72f6e441f9e9484',  # SYN
        '0x42f6f551ae042cbe50c739158b4f0cac0edb9096',  # NRV
        '0x130025ee738a66e691e6a7a62381cb33c6d9ae83',  # JUMP
        '0x0fe9778c005a5a6115cbe12b0568a2d50b765a51',  # NFD
        '0xc13b7a43223bb9bf4b69bd68ab20ca1b79d81c75',  # JGN
        '0x88918495892baf4536611e38e75d771dc6ec0863',  # gOHM
        '0xc8699abbba90c7479dedccef19ef78969a2fc608',  # USDB
    ],
    'polygon': [
        '0xf8f9efc0db77d8881500bb06ff5d6abc3070e695',  # SYN
        '0x8f3cf7ad23cd3cadbd9735aff958023239c6a063',  # DAI
        '0x2791bca1f2de4661ed88a30c99a7a9449aa84174',  # USDC
        '0xc2132d05d31c914a87c6611c10748aeb04b58e8f',  # USDT
        '0xb6c473756050de474286bed418b77aeac39b02af',  # nUSD
        '0x128a587555d1148766ef4327172129b50ec66e5d',  # USD-LP
        '0x0a5926027d407222f8fe20f24cb16e103f617046',  # NFD
        '0xd8ca34fd379d9ca3c6ee3b3905678320f5b45195',  # gOHM
        '0xeee3371b89fc43ea970e908536fcddd975135d8a',  # DOG
        '0x48a34796653afdaa1647986b33544c911578e767',  # synFRAX
        '0x7ceb23fd6bc0add59e62ac25578270cff1b9f619',  # WETH
        '0xfa1fbb8ef55a4855e5688c0ee13ac3f202486286',  # USDB
    ],
    'avalanche': [
        '0xd586e7f844cea2f87f50152665bcbc2c279d8d70',  # DAI
        '0xa7d7079b0fead91f3e65f86e8915cb59c1a4c664',  # USDC
        '0xc7198437980c041c805a1edcba50c1ce5db95118',  # USDT
        '0xcfc37a6ab183dd4aed08c204d1c2773c0b1bdf46',  # nUSD
        '0x55904f416586b5140a0f666cf5acf320adf64846',  # USD-LP
        '0x1f1e7c893855525b303f99bdf5c3c05be09ca251',  # SYN
        '0xf1293574ee43950e7a8c9f1005ff097a9a713959',  # NFD
        '0x19e1ae0ee35c0404f835521146206595d37981ae',  # nETH
        '0x321e7092a180bb43555132ec53aaa65a5bf84251',  # gOHM
        '0xcc5672600b948df4b665d9979357bef3af56b300',  # synFRAX
        '0x53f7c5869a859f0aec3d334ee8b4cf01e3492f21',  # avWETH
        '0x62edc0692bd897d2295872a9ffcac5425011c661',  # GMX
        '0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7',  # WAVAX
        #'0x20a9dc684b4d0407ef8c9a302beaaa18ee15f656',  # GMX
        '0x4bfc90322dd638f81f034517359bd447f8e0235a',  # NEWO
        '0xccbf7c451f81752f7d2237f2c18c371e6e089e69',  # SDT
        '0x5ab7084cb9d270c2cb052dd30dbecbca42f8620c',  # USDB
    ],
    'arbitrum': [
        '0xda10009cbd5d07dd0cecc66161fc93d7c9000da1',  # DAI
        '0x080f6aed32fc474dd5717105dba5ea57268f46eb',  # SYN
        '0xff970a61a04b1ca14834a43f5de4533ebddb5cc8',  # USDC
        '0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9',  # USDT
        '0x2913e812cf0dcca30fb28e6cac3d2dcff4497688',  # nUSD
        '0xe264cb5a941f98a391b9d5244378edf79bf5c19e',  # USD-LP
        '0xfea7a6a0b346362bf88a9e4a88416b77a57d6c2a',  # MIM
        '0x3ea9b0ab55f34fb188824ee288ceaefc63cf908e',  # nETH
        '0x82af49447d8a07e3bd95bd0d56f35241523fbab1',  # WETH
        '0x8d9ba570d6cb60c7e3e0f31343efe75ab8e65fb1',  # gOHM
        '0x85662fd123280827e11c59973ac9fcbe838dc3b4',  # synFRAX
        '0xfc5a1a6eb076a2c7ad06ed22c90d7e710e35ad0a',  # GMX
        '0x0877154a755b24d499b8e2bd7ecd54d3c92ba433',  # NEWO
        '0x1a4da80967373fd929961e976b4b53ceec063a15',  # LUNA
    ],
    'fantom': [
        '0x04068da6c83afcfa0e13ba15a6696662335d5b75',  # USDC
        '0x049d68029688eabf473097a2fc38ef61633a3c7a',  # fUSDT
        '0x43cf58380e69594fa2a5682de484ae00edd83e94',  # USD-LP
        '0x82f0b8b456c1a451378467398982d4834b6829c1',  # MIM
        '0xed2a7edd7413021d440b09d654f3b87712abab66',  # nUSD
        '0xe55e19fb4f2d85af758950957714292dac1e25b2',  # SYN
        '0x78de9326792ce1d6eca0c978753c6953cdeedd73',  # JUMP
        '0x91fa20244fb509e8289ca630e5db3e9166233fdc',  # gOHM
        '0x1852f70512298d56e9c8fdd905e02581e04ddb2a',  # synFRAX
        '0x67c10c397dd0ba417329543c1a40eb48aaa7cd00',  # nETH
        '0x74b23882a30290451a17c44f4f05243b6b58c76d',  # WETH
        '0xe3c82a836ec85311a433fbd9486efaf4b1afbf48',  # SDT
        '0x6fc9383486c163fa48becdec79d6058f984f62ca',  # USDB
    ],
    'harmony': [
        '0xe55e19fb4f2d85af758950957714292dac1e25b2',  # SYN
        '0xef977d2f931c1978db5f6747666fa1eacb0d0339',  # 1DAI
        '0x985458e523db3d53125813ed68c274899e9dfab4',  # 1USDC
        '0x3c2b8be99c50593081eaa2a724f0b8285f5aba8f',  # 1USDT
        '0xed2a7edd7413021d440b09d654f3b87712abab66',  # nUSD
        '0xcf664087a5bb0237a0bad6742852ec6c8d69a27a',  # ONE
        '0x1852f70512298d56e9c8fdd905e02581e04ddb2a',  # synFRAX
        '0xfa7191d292d5633f702b0bd7e3e3bccc0e633200',  # old synFRAX
        '0x67c10c397dd0ba417329543c1a40eb48aaa7cd00',  # gOHM
        '0x0b5740c6b4a97f90ef2f0220651cca420b868ffb',  # nETH
        '0xe3c82a836ec85311a433fbd9486efaf4b1afbf48',  # SDT
    ],
    'boba': [
        '0x66a2a913e447d6b4bf33efbec43aaef87890fbbc',  # USDC
        '0xb554a55358ff0382fb21f0a478c3546d1106be8c',  # SYN
        '0x5de1677344d3cb0d7d465c10b72a8f60699c062d',  # USDT
        '0xdeaddeaddeaddeaddeaddeaddeaddeaddead0000',  # WETH
        '0x96419929d7949d6a801a6909c145c8eef6a40431',  # nETH
        '0x6b4712ae9797c199edd44f897ca09bc57628a1cf',  # nUSD
        '0xf74195bb8a5cf652411867c5c2c5b8c2a402be35',  # DAI
        '0xd203de32170130082896b4111edf825a4774c18e',  # WETH
        '0xd22c0a4af486c7fa08e282e9eb5f30f9aaa62c95',  # gOHM
    ],
    'moonriver': [
        '0xd80d8688b02b3fd3afb81cdb124f188bb5ad0445',  # SYN
        '0xe96ac70907fff3efee79f502c985a7a21bce407d',  # synFRAX
        '0x1a93b23281cc1cde4c4741353f3064709a16197d',  # FRAX
        '0x3bf21ce864e58731b6f28d68d5928bcbeb0ad172',  # gOHM
        '0x76906411d07815491a5e577022757ad941fb5066',  # veSOLAR
        '0x98878b06940ae243284ca214f92bb71a2b032b8a',  # WMOVR
        '0x3e193c39626bafb41ebe8bdd11ec7cca9b3ec0b2',  # USDB
    ],
    'optimism': [
        '0x809dc529f07651bd43a172e8db6f4a7a0d771036',  # nETH
        '0x5a5fff6f753d7c11a56a52fe47a177a87e431655',  # SYN
        '0x121ab82b49b2bc4c7901ca46b8277962b4350204',  # WETH
        '0x0b5740c6b4a97f90ef2f0220651cca420b868ffb',  # gOHM
        '0x931b8f17764362a3325d30681009f0edd6211231',  # LUNA
    ],
    'aurora': [
        '0xd80d8688b02b3fd3afb81cdb124f188bb5ad0445',  # SYN
        '0xb12bfca5a55806aaf64e99521918a4bf0fc40802',  # USDC
        '0x4988a896b1227218e4a686fde5eabdcabd91571f',  # USDT
        '0x07379565cd8b0cae7c60dc78e7f601b34af2a21c',  # nUSD
    ],
    'moonbeam': [
        '0x3192ae73315c3634ffa217f71cf6cbc30fee349a',  # WETH
        '0xbf180c122d85831dcb55dc673ab47c8ab9bcefb4',  # nETH
        '0xf44938b0125a6662f9536281ad2cd6c499f22004',  # SYN
        '0x0db6729c03c85b0708166ca92801bcb5cac781fc',  # veSOLAR
        '0xd2666441443daa61492ffe0f37717578714a4521',  # gOHM
        '0xdd47a348ab60c61ad6b60ca8c31ea5e00ebfab4f',  # synFRAX
        '0x1d4c2a246311bb9f827f4c768e277ff5787b7d7e',  # MOVR
        '0xa1f8890e39b4d8e33efe296d698fe42fb5e59cc3',  # AVAX
    ],
    'cronos': [
        '0xfd0f80899983b8d46152aa1717d76cba71a31616',  # SYN
        '0x396c9c192dd323995346632581bef92a31ac623b',  # nUSD
        '0xbb0a63a6ca2071c6c4bcac11a1a317b20e3e999c',  # gOHM
    ],
    'metis': [
        '0xfb21b70922b9f6e3c6274bcd6cb1aa8a0fe20b80',  # gOHM
        '0x961318fc85475e125b99cc9215f62679ae5200ab',  # nUSD
        '0x67c10c397dd0ba417329543c1a40eb48aaa7cd00',  # SYN
        '0xea32a96608495e54156ae48931a7c20f0dcc1a21',  # USDC
        '0x931b8f17764362a3325d30681009f0edd6211231',  # nETH
        '0x420000000000000000000000000000000000000a',  # WETH 
    ]
}

MAX_UINT8 = 2**8 - 1


class TokenInfo(TypedDict):
    _contract: Contract
    name: str
    decimals: int
    symbol: str


TOKENS_INFO: Dict[str, Dict[str, TokenInfo]] = defaultdict(dict)
__jobs: List[Greenlet] = []


def __cb(w3: Web3, chain: str, token: str) -> None:
    contract = w3.eth.contract(w3.toChecksumAddress(token), abi=ERC20_BARE_ABI)

    decimals = contract.functions.decimals().call()
    name = contract.functions.name().call()
    symbol = contract.functions.symbol().call()

    TOKENS_INFO[chain].update({
        token.lower():
        TokenInfo(_contract=contract,
                  name=name,
                  symbol=symbol,
                  decimals=decimals)
    })


__pool = Pool(size=16)
for chain, tokens in TOKENS.items():
    w3: Web3 = SYN_DATA[chain]['w3']

    for token in tokens:
        assert token not in TOKENS_INFO[chain], \
            f'duped token? {token} @ {chain} | {TOKENS_INFO[chain][token]}'

        __jobs.append(__pool.spawn(__cb, w3, chain, token))

gevent.joinall(__jobs, raise_error=True)

# Wrapper of GMX.
TOKENS_INFO['avalanche'].update({
    '0x20a9dc684b4d0407ef8c9a302beaaa18ee15f656':
    TOKENS_INFO['avalanche']['0x62edc0692bd897d2295872a9ffcac5425011c661']
})

TOKEN_DECIMALS: Dict[str, Dict[str, int]] = defaultdict(dict)

# `TOKEN_DECIMALS` is an abstraction of `TOKENS_INFO`.
for chain, v in TOKENS_INFO.items():
    for token, data in v.items():
        assert token not in TOKEN_DECIMALS[chain], \
            f'duped token? {token} @ {chain} | {TOKEN_DECIMALS[chain][token]}'

        TOKEN_DECIMALS[chain].update({token: data['decimals']})

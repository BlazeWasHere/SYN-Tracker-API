#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import cast
import os

from web3.middleware.geth_poa import geth_poa_middleware
from dotenv import load_dotenv, find_dotenv
from web3 import Web3

load_dotenv(find_dotenv('.env.sample'))
load_dotenv(override=True)

ETH_RPC = cast(str, os.getenv('ETH_RPC'))
AVAX_RPC = cast(str, os.getenv('AVAX_RPC'))
BSC_RPC = cast(str, os.getenv('BSC_RPC'))
POLYGON_RPC = cast(str, os.getenv('POLYGON_RPC'))
ARB_RPC = cast(str, os.getenv('ARB_RPC'))
FTM_RPC = cast(str, os.getenv('FTM_RPC'))
HARMONY_RPC = cast(str, os.getenv('HARMONY_RPC'))
BOBA_RPC = cast(str, os.getenv('BOBA_RPC'))
MOVR_RPC = cast(str, os.getenv('MOVR_RPC'))
OPTIMISM_RPC = cast(str, os.getenv('OPTIMISM_RPC'))

BEGIN_DATE = '2021-01-01'

AIRDROP = {
    'arbitrum': {
        '2021-11-28': 0.003,
        BEGIN_DATE: 0
    },
    'avalanche': {
        '2021-11-20': 0.025,
        BEGIN_DATE: 0.05
    },
    'boba': {
        BEGIN_DATE: 0.005
    },
    'bsc': {
        '2021-10-24': 0.002,
        BEGIN_DATE: 0.001
    },
    'fantom': {
        BEGIN_DATE: 0.4
    },
    'harmony': {
        BEGIN_DATE: 0.1
    },
    'moonriver': {
        BEGIN_DATE: 0.002
    },
    'optimism': {
        '2021-11-28': 0.002,
        BEGIN_DATE: 0
    },
    'polygon': {
        '2021-10-18': 0.02,
        BEGIN_DATE: 0.0003
    }
}

CHAINS = {
    'ethereum': {
        'w3': Web3(Web3.HTTPProvider(ETH_RPC)),
        'id': 1,
        'max_blocks': 5000,
        'bridge': '0x2796317b0fF8538F253012862c06787Adfb8cEb6',
        'scan_key': cast(str, os.getenv('ETH_SCAN_KEY'))
    },
    'avalanche': {
        'w3': Web3(Web3.HTTPProvider(AVAX_RPC)),
        'id': 43114,
        'max_blocks': 5000,
        'bridge': '0xC05e61d0E7a63D27546389B7aD62FdFf5A91aACE',
        'scan_key': cast(str, os.getenv('AVA_SCAN_KEY'))
    },
    'bsc': {
        'w3': Web3(Web3.HTTPProvider(BSC_RPC)),
        'id': 56,
        'max_blocks': 1000,
        'bridge': '0xd123f70ae324d34a9e76b67a27bf77593ba8749f',
        'scan_key': cast(str, os.getenv('BSC_SCAN_KEY'))
    },
    'polygon': {
        'w3': Web3(Web3.HTTPProvider(POLYGON_RPC)),
        'id': 137,
        'max_blocks': 5000,
        'bridge': '0x8F5BBB2BB8c2Ee94639E55d5F41de9b4839C1280',
        'scan_key': cast(str, os.getenv('POL_SCAN_KEY'))
    },
    'arbitrum': {
        'w3': Web3(Web3.HTTPProvider(ARB_RPC)),
        'id': 42161,
        'max_blocks': 200000,
        'bridge': '0x6F4e8eBa4D337f874Ab57478AcC2Cb5BACdc19c9',
        'scan_key': cast(str, os.getenv('ARB_SCAN_KEY'))
    },
    'fantom': {
        'w3': Web3(Web3.HTTPProvider(FTM_RPC)),
        'id': 250,
        'max_blocks': 5000,
        'bridge': '0xAf41a65F786339e7911F4acDAD6BD49426F2Dc6b',
        'scan_key': cast(str, os.getenv('FTM_SCAN_KEY'))
    },
    'harmony': {
        'w3': Web3(Web3.HTTPProvider(HARMONY_RPC)),
        'id': 1666600000,
        'max_blocks': 1000,
        'bridge': '0xAf41a65F786339e7911F4acDAD6BD49426F2Dc6b',
    },
    'boba': {
        'w3': Web3(Web3.HTTPProvider(BOBA_RPC)),
        'id': 288,
        'max_blocks': 2000,
        'bridge': '0x432036208d2717394d2614d6697c46DF3Ed69540'
    },
    'moonriver': {
        'w3': Web3(Web3.HTTPProvider(MOVR_RPC)),
        'id': 1285,
        'max_blocks': 1000,
        'bridge': '0xaeD5b25BE1c3163c907a471082640450F928DDFE',
    },
    'optimism': {
        'w3': Web3(Web3.HTTPProvider(OPTIMISM_RPC)),
        'id': 10,
        'max_blocks': 5000,
        'bridge': '0xAf41a65F786339e7911F4acDAD6BD49426F2Dc6b',
    }
}

CHAINS['avalanche']['w3'].middleware_onion.inject(geth_poa_middleware, layer=0)
CHAINS['bsc']['w3'].middleware_onion.inject(geth_poa_middleware, layer=0)
CHAINS['polygon']['w3'].middleware_onion.inject(geth_poa_middleware, layer=0)

BLOCK_START = {
    'ethereum': {
        # 'bridge': 13033669,
        'bridge': 13717847,  # 2021-12-01
        # 'bridge': 13749029,  # 2021-12-06
    },
    'avalanche': {
        'bridge': 3376709,
    },
    'bsc': {
        'bridge': 10065475,
        # 'bridge': 13089738,  # 2021-12-01
    },
    'polygon': {
        'bridge': 18026806,
    },
    'arbitrum': {
        'bridge': 657404,
    },
    'fantom': {
        'bridge': 18503502,
    },
    'harmony': {
        'bridge': 18646320,
    },
    'boba': {
        'bridge': 16188,
    },
    'moonriver': {
        'bridge': 890949,
    },
    'optimism': {
        'bridge': 30718,
    }
}

BRIDGE_CONFIG = {
    'address': '0x7FD806049608B7d04076B8187dd773343e0589e6',
}

POOLS_NUSD = {
    'ethereum': {
        'address': '0x1116898DdA4015eD8dDefb84b6e8Bc24528Af2d8',
    },
    'avalanche': {
        'address': '0xED2a7edd7413021d440b09D654f3b87712abAB66',
    },
    'bsc': {
        'address': '0x28ec0B36F0819ecB5005cAB836F4ED5a2eCa4D13',
    },
    'polygon': {
        'address': '0x85fCD7Dd0a1e1A9FCD5FD886ED522dE8221C3EE5',
    },
    'arbitrum': {
        'address': '0x0Db3FE3B770c95A0B99D1Ed6F2627933466c0Dd8',
    },
    'fantom': {
        'address': '0x2913E812Cf0dcCA30FB28E6Cac3d2DCFF4497688',
    },
    'harmony': {
        'address': '0x3ea9b0ab55f34fb188824ee288ceaefc63cf908e',
    },
    'boba': {
        'address': '0x75FF037256b36F15919369AC58695550bE72fead',
    },
}

POOLS_NETH = {
    'arbitrum': {
        'address': '0xa067668661C84476aFcDc6fA5D758C4c01C34352',
    },
    'boba': {
        'address': '0x753bb855c8fe814233d26Bb23aF61cb3d2022bE5',
    },
    'optimism': {
        'address': '0xE27BFf97CE92C3e1Ff7AA9f86781FDd6D48F5eE9',
    }
}

TOKENS = {
    'ethereum': {
        'nusd': '0x1b84765de8b7566e4ceaf4d0fd3c5af52d3dde4f',
    },
    'avalanche': {
        'nusd': '0xcfc37a6ab183dd4aed08c204d1c2773c0b1bdf46',
    },
    'bsc': {
        'nusd': '0x23b891e5c62e0955ae2bd185990103928ab817b3',
    },
    'polygon': {
        'nusd': '0xb6c473756050de474286bed418b77aeac39b02af',
    },
    'arbitrum': {
        'nusd': '0x2913e812cf0dcca30fb28e6cac3d2dcff4497688',
    },
    'fantom': {
        'nusd': '0xed2a7edd7413021d440b09d654f3b87712abab66',
    },
    'harmony': {
        'nusd': '0xed2a7edd7413021d440b09d654f3b87712abab66',
    },
    'boba': {
        'nusd': '0x6b4712ae9797c199edd44f897ca09bc57628a1cf',
    },
    'moonriver': {},
    'optimism': {}
}

SYMBOLS = {
    'nusd': 'nUSD',
    'syn': 'SYN',
    'neth': 'nETH',
    'weth': 'nETH',
    'high': 'HIGH',
    'dog': 'DOG',
    'frax': 'synFRAX',
    'nfd': 'NFD',
    'jump': 'JUMP',
    'synfrax': 'synFRAX',
    'gohm': 'gOHM',
}

ALIAS = {
    'weth': 'neth',
    'synfrax': 'frax',
}

METHODS = {
    '0x1cf5f07f': 'withdraw',
    '0xd57eafac': 'withdrawAndRemove',
    '0x20d7b327': 'mint',
    '0x17357892': 'mintAndSwap',
}

EVENTS_IN = {
    '0x8b0afdc777af6946e53045a4a75212769075d30455a212ac51c9b16f9c5c9b26':
    'TokenWithdraw',
    '0xc1a608d0f8122d014d03cc915a91d98cef4ebaf31ea3552320430cba05211b6d':
    'TokenWithdrawAndRemove',
    '0xbf14b9fde87f6e1c29a7e0787ad1d0d64b4648d8ae63da21524d9fd0f283dd38':
    'TokenMint',
    '0x4f56ec39e98539920503fd54ee56ae0cbebe9eb15aa778f18de67701eeae7c65':
    'TokenMintAndSwap',
}

EVENTS_OUT = {
    '0xdc5bad4651c5fbe9977a696aadc65996c468cde1448dd468ec0d83bf61c4b57c':
    'TokenRedeem',
    '0x91f25e9be0134ec851830e0e76dc71e06f9dade75a9b84e9524071dbbc319425':
    'TokenRedeemAndSwap',
    '0x9a7024cde1920aa50cdde09ca396229e8c4d530d5cfdc6233590def70a94408c':
    'TokenRedeemAndRemove',
    '0xda5273705dbef4bf1b902a131c2eac086b7e1476a8ab0cb4da08af1fe1bd8e3b':
    'TokenDeposit',
    '0x79c15604b92ef54d3f61f0c40caab8857927ca3d5092367163b4562c1699eb5f':
    'TokenDepositAndSwap',
}

GLOBAL_MAP = {
    '0x3bf21ce864e58731b6f28d68d5928bcbeb0ad172': 'gohm',  # Moonriver
}

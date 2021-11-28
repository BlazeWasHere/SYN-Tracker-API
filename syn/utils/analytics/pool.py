#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import cast

from web3.types import LogReceipt
from web3 import Web3

from syn.utils.data import SYN_DATA, POOL_ABI
from syn.utils.helpers import convert

TOPICS = {
    '0xc6c1e0630dbe9130cc068028486c0d118ddcea348550819defd5cb8c257f8a38':
    'TokenSwap',
    '0xd88ea5155021c6f8dafa1a741e173f595cdf77ce7c17d43342131d7f06afdfe5':
    'NewSwapFee',
    '0xab599d640ca80cde2b09b128a4154a8dfe608cb80f4c9399c8b954b01fd35f38':
    'NewAdminFee',
    '0x189c623b666b1b45b83d7178f39b8c087cb09774317ca2f53c2d3c3726f222a2':
    'AddLiquidity',
    '0x43fb02998f4e03da2e0e6fff53fdbf0c40a9f45f145dc377fc30615d7d7a8a64':
    'RemoveLiquidityOne',
    '0x3631c28b1f9dd213e0319fb167b554d76b6c283a41143eb400a0d1adb1af1755':
    'RemoveLiquidityImbalance',
}

#: NOTE: all the fees here are INITIAL fees which can be changed later on,
#: thus us tracking `NewSwapFee` and `NewAdminFee`
#: Similar schema as :file:`syn/utils/explorer/data.py#L90`
# TODO(blaze): add rest of the fees. (ones set to 0)
POOLS = {
    'ethereum': {
        'nusd': {
            '0x1116898dda4015ed8ddefb84b6e8bc24528af2d8': {
                'admin': 0,
                'swap': 4000000,
            },
        },
    },
    'avalanche': {
        'nusd': {
            '0xed2a7edd7413021d440b09d654f3b87712abab66': {
                'admin': 6000000000,
                'swap': 4000000
            },
        },
    },
    'bsc': {
        'nusd': {
            '0x28ec0b36f0819ecb5005cab836f4ed5a2eca4d13': {
                'admin': 6000000000,
                'swap': 4000000,
            },
        },
    },
    'polygon': {
        'nusd': {
            '0x85fcd7dd0a1e1a9fcd5fd886ed522de8221c3ee5': {
                'admin': 6000000000,
                'swap': 4000000,
            },
        },
    },
    'arbitrum': {
        'nusd': {
            '0x0db3fe3b770c95a0b99d1ed6f2627933466c0dd8': {
                'admin': 0,
            },
        },
        'neth': {
            '0xa067668661c84476afcdc6fa5d758c4c01c34352': {
                'admin': 0,
                'swap': 0,
            },
        },
    },
    'fantom': {
        'nusd': {
            '0x2913e812cf0dcca30fb28e6cac3d2dcff4497688': {
                'admin': 6000000000,
                'swap': 4000000,
            },
        },
    },
    'harmony': {
        'nusd': {
            '0x3ea9b0ab55f34fb188824ee288ceaefc63cf908e': {
                'admin': 0,
                'swap': 0,
            },
        },
    },
    'boba': {
        'nusd': {
            '0x75ff037256b36f15919369ac58695550be72fead': {
                'admin': 0,
                'swap': 0,
            },
        },
        'neth': {
            '0x753bb855c8fe814233d26bb23af61cb3d2022be5': {
                'admin': 0,
                'swap': 0,
            },
        },
    },
    'optimism': {
        'neth': {
            '0xe27bff97ce92c3e1ff7aa9f86781fdd6d48f5ee9': {
                'admin': 0,
                'swap': 0,
            },
        },
    },
}

# https://github.com/synapsecns/synapse-contracts/blob/master/contracts/amm/SwapUtils.sol
FEE_DENOMINATOR = 10**10


def pool_callback(chain: str, address: str, log: LogReceipt) -> None:
    w3: Web3 = SYN_DATA[chain]['w3']
    contract = w3.eth.contract(w3.toChecksumAddress(address), abi=POOL_ABI)

    topic = cast(str, convert(log['topics'][0]))
    if topic not in TOPICS:
        raise RuntimeError(f'sanity check? got invalid topic: {topic}')

    event = TOPICS[topic]
    data = contract.events[event]().processLog(log)
    # TODO(blaze): finish.
    print(chain, event, log['transactionHash'].hex(), data)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Any, Dict, Literal, Optional, Union, cast, get_args
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import logging

from web3.types import LogReceipt
import simplejson as json
from web3 import Web3

from syn.utils.data import SYN_DATA, POOL_ABI, TOKEN_DECIMALS, LOGS_REDIS_URL
from syn.utils.helpers import convert, get_all_keys, handle_decimals
from syn.utils.price import CoingeckoIDS, get_historic_price
from syn.utils.explorer.data import TOKENS_IN_POOL

Pools = Literal['nusd', 'neth']

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
# TODO: pls somone check these numbers, whoever is reading this code, ty!
POOLS: Dict[str, Dict[str, Dict[str, Union[str, int]]]] = {
    'ethereum': {
        'nusd': {
            'address': '0x1116898dda4015ed8ddefb84b6e8bc24528af2d8',
            'admin': 0,
            'swap': 4000000,
        }
    },
    'avalanche': {
        'nusd': {
            'address': '0xed2a7edd7413021d440b09d654f3b87712abab66',
            'admin': 6000000000,
            'swap': 4000000
        },
        'neth': {
            'address': '0x77a7e60555bC18B4Be44C181b2575eee46212d44',
            'admin': 6000000000,
            'swap': 4000000,
        },
    },
    'bsc': {
        'nusd': {
            'address': '0x28ec0b36f0819ecb5005cab836f4ed5a2eca4d13',
            'admin': 6000000000,
            'swap': 4000000,
        },
    },
    'polygon': {
        'nusd': {
            'address': '0x85fcd7dd0a1e1a9fcd5fd886ed522de8221c3ee5',
            'admin': 6000000000,
            'swap': 4000000,
        },
    },
    'arbitrum': {
        'nusd': {
            # Check.
            'address': '0x0db3fe3b770c95a0b99d1ed6f2627933466c0dd8',
            'admin': 6000000000,
            'swap': 4000000,
        },
        'neth': {
            # Check.
            'address': '0xa067668661c84476afcdc6fa5d758c4c01c34352',
            'admin': 6000000000,
            'swap': 4000000,
        },
    },
    'fantom': {
        'nusd': {
            'address': '0x2913e812cf0dcca30fb28e6cac3d2dcff4497688',
            'admin': 6000000000,
            'swap': 4000000,
        },
    },
    'harmony': {
        'nusd': {
            # Check.
            'address': '0x3ea9b0ab55f34fb188824ee288ceaefc63cf908e',
            'admin': 6000000000,
            'swap': 4000000,
        },
    },
    'boba': {
        'nusd': {
            # Check.
            'address': '0x75ff037256b36f15919369ac58695550be72fead',
            'admin': 6000000000,
            'swap': 4000000,
        },
        'neth': {
            # Check.
            'address': '0x753bb855c8fe814233d26bb23af61cb3d2022be5',
            'admin': 6000000000,
            'swap': 4000000,
        },
    },
    'optimism': {
        'neth': {
            # Check.
            'address': '0xe27bff97ce92c3e1ff7aa9f86781fdd6d48f5ee9',
            'admin': 6000000000,
            'swap': 4000000,
        },
    },
}

# https://github.com/synapsecns/synapse-contracts/blob/b3829f7c2177e9daf35d176713243acb6c43ea2b/contracts/amm/SwapUtils.sol#L112
FEE_DENOMINATOR = 10**10
FEE_DECIMALS = 10

_chain_fee: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(dict)


def _address_to_pool(chain: str,
                     address: str) -> Union[Literal['nusd'], Literal['neth']]:
    for k, v in POOLS[chain].items():
        if cast(str, v['address']).lower() == address.lower():
            return k  # type: ignore

    raise RuntimeError(f"{address} not found in {chain}'s pools")


def pool_callback(chain: str, address: str, log: LogReceipt) -> None:
    w3: Web3 = SYN_DATA[chain]['w3']
    contract = w3.eth.contract(w3.toChecksumAddress(address), abi=POOL_ABI)

    topic = cast(str, convert(log['topics'][0]))
    if topic not in TOPICS:
        raise RuntimeError(f'sanity check? got invalid topic: {topic}')

    event = TOPICS[topic]
    data = contract.events[event]().processLog(log)
    pool = _address_to_pool(chain, address)

    block_n = log['blockNumber']
    timestamp = w3.eth.get_block(block_n)['timestamp']  # type: ignore
    date = datetime.utcfromtimestamp(timestamp).date()

    if pool not in _chain_fee[chain]:
        _chain_fee[chain][pool] = {
            'admin': cast(int, POOLS[chain][pool]['admin']),
            'swap': cast(int, POOLS[chain][pool]['swap']),
        }

    TOPICS_REVERSE = {v: k for k, v in TOPICS.items()}
    admin_fee = _chain_fee[chain][pool]['admin']
    swap_fee = _chain_fee[chain][pool]['swap']
    data = data['args']

    newfee: Optional[Union[Literal['swap'], Literal['admin']]] = None

    # Wen match-case syntax?
    if topic in [
            TOPICS_REVERSE['RemoveLiquidityOne'], TOPICS_REVERSE['TokenSwap']
    ]:
        decimals = TOKEN_DECIMALS[chain][
                    TOKENS_IN_POOL[chain][pool][data['boughtId']].lower()]
        total_fees = Decimal(
            data['tokensBought']) * Decimal(swap_fee) / Decimal(
                (FEE_DENOMINATOR - swap_fee) * 10**decimals)
        admin_lps_fees = handle_decimals(total_fees * admin_fee, FEE_DECIMALS)
        lp_fees = total_fees - admin_lps_fees
        volume = handle_decimals(data['tokensBought'], decimals)
    elif topic == TOPICS_REVERSE['NewSwapFee']:
        _chain_fee[chain][pool]['swap'] = data['newSwapFee']
        newfee = 'swap'
    elif topic == TOPICS_REVERSE['NewAdminFee']:
        _chain_fee[chain][pool]['admin'] = data['newAdminFee']
        newfee = 'admin'
    elif topic in [
            TOPICS_REVERSE['AddLiquidity'],
            TOPICS_REVERSE['RemoveLiquidityImbalance']
    ]:
        fees = data['fees']
        amounts = data['tokenAmounts']
        # Pools are (WETH, NETH) & (STABLES) - all practically have the same peg.
        total_fees = Decimal(0)
        volume = Decimal(0)

        for i, token in TOKENS_IN_POOL[chain][pool].items():
            decimals = TOKEN_DECIMALS[chain][token.lower()]
            total_fees += handle_decimals(fees[i], decimals)
            volume += handle_decimals(amounts[i], decimals)

        admin_lps_fees = handle_decimals(total_fees * admin_fee, FEE_DECIMALS)
        lp_fees = total_fees - admin_lps_fees
    else:
        print(topic, 'unsupported', data, chain, log)

        # TODO: dont skip...
        logging.critical(
            f'{chain} is skipping block({block_n}) in pool callback')
        LOGS_REDIS_URL.rpush(f'{chain}:pool:skipped', block_n)
        return

    if topic in [
        TOPICS_REVERSE['AddLiquidity'],
        TOPICS_REVERSE['RemoveLiquidityOne'],
        TOPICS_REVERSE['RemoveLiquidityImbalance']
    ]:
        tx_type = ':add_remove'
    elif topic == TOPICS_REVERSE['TokenSwap']:
        # We want to track "base swaps" - swaps between non-nUSD tokens
        # Swaps on Ethereum are always "base"
        # Swaps on other chains are base if both tokens ID > 0,
        # as nUSD is always the first token in the pool (ID = 0)
        if chain == 'ethereum' or \
                (data['soldId'] > 0 and data['boughtId'] > 0):
            tx_type = ':swap_base'
        else:
            tx_type = ':swap_nusd'
    else:
        tx_type = ''

    key = f'{chain}:pool:{date}:{pool}{tx_type}'
    if newfee is not None:
        value = _chain_fee[chain][newfee]
    else:
        # Vars WILL NOT be unbound, stupid linter.
        value = {
            'volume': volume,  # type: ignore
            'lp_fees': lp_fees,  # type: ignore
            'admin_fees': admin_lps_fees,  # type: ignore
            'tx_count': 1,
        }

    if (ret := LOGS_REDIS_URL.get(key)) is not None:
        ret = json.loads(ret, use_decimal=True)

        if newfee is not None:
            # New fee was set.
            ret['newfee_' + newfee] = value
        else:
            # A swap event.
            ret['admin_fees'] += value['admin_fees']
            ret['lp_fees'] += value['lp_fees']
            ret['volume'] += value['volume']

            # NOTE: many aggregators create txs with many pool events in 1 tx,
            # so in reality this is more like `event_count` rather than `tx_count`.
            # Quite inconsistent with :func:`bridge_callback`.
            ret['tx_count'] += 1

        LOGS_REDIS_URL.set(key, json.dumps(ret))
    else:
        # TODO: possibly check if we got an earlier block before the one set in
        # :func:`bridge_callback`, but it adds computational cost.
        LOGS_REDIS_URL.set(key, json.dumps(value))

    LOGS_REDIS_URL.set(f'{chain}:pool:{address}:MAX_BLOCK_STORED',
                       log['blockNumber'])
    LOGS_REDIS_URL.set(f'{chain}:pool:{address}:TX_INDEX',
                       log['transactionIndex'])


def get_swap_volume_for_pool(pool: Pools, chain: str) -> Dict[str, Any]:
    assert pool in get_args(Pools), f'invalid pool: {pool!r}'

    res = defaultdict(dict)

    for tx_type in ['add_remove', 'swap_base', 'swap_nusd']:
        ret: Dict[str, Dict[str, str]] = get_all_keys(
            f'{chain}:pool:*:{pool}:{tx_type}',
            client=LOGS_REDIS_URL,
            index=2,
            serialize=True
        )

        for k, v in ret.items():
            # For simplicity's sake, we disregard virtual prices & pool token
            # fluctuations, so nusd, dai, usdc, busd, ... = $1
            if pool == 'neth':
                price = get_historic_price(CoingeckoIDS.ETH, k)
            elif pool == 'nusd':
                price = 1

            res[k][tx_type] = {
                'volume': Decimal(v['volume']),
                'lp_fees': Decimal(v['lp_fees']),
                'admin_fees': Decimal(v['admin_fees']),
                'tx_count': v['tx_count'],
            }

            res[k][tx_type].update({
                'volume_usd': price * res[k][tx_type]['volume'],
                'lp_fees_usd': price * res[k][tx_type]['lp_fees'],
                'admin_fees_usd': price * res[k][tx_type]['admin_fees'],
            })

    return res

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Dict, Union, List
from collections import defaultdict

from syn.utils.data import SYN_DATA, TOKEN_DECIMALS, LOGS_REDIS_URL
from syn.utils.helpers import add_to_dict, raise_if, get_all_keys
from syn.utils.contract import get_all_tokens_in_pool, call_abi
from syn.utils.price import CoingeckoIDS, get_historic_price, \
    get_historic_price_for_address
from syn.utils.analytics.volume import create_totals
from syn.utils.cache import timed_cache

from gevent.greenlet import Greenlet
from gevent.pool import Pool
import gevent

pool = Pool()

# Map the chain to their native token (what gas is paid in).
_chain_to_cgid = {
    'ethereum': CoingeckoIDS.ETH,
    'avalanche': CoingeckoIDS.AVAX,
    'bsc': CoingeckoIDS.BNB,
    'polygon': CoingeckoIDS.MATIC,
    'arbitrum': CoingeckoIDS.ETH,
    'fantom': CoingeckoIDS.FTM,
    'harmony': CoingeckoIDS.ONE,
    'boba': CoingeckoIDS.ETH,
    'moonriver': CoingeckoIDS.MOVR,
    'optimism': CoingeckoIDS.ETH,
}


@timed_cache(60, maxsize=50)
def get_admin_fee(chain: str,
                  index: int,
                  block: Union[int, str] = 'latest',
                  func: str = 'pool_contract') -> int:
    return call_abi(SYN_DATA[chain],
                    func,
                    'getAdminBalance',
                    index,
                    call_args={'block_identifier': block})


def get_admin_fees(chain: str,
                   block: Union[int, str] = 'latest',
                   handle_decimals: bool = False,
                   tokens: List[str] = None) -> Dict[str, float]:
    if tokens is None:
        tokens = get_all_tokens_in_pool(chain)

    res: Dict[str, float] = {}

    if tokens:
        for i, token in enumerate(tokens):
            res[token] = get_admin_fee(chain, i, block)

            if handle_decimals:
                res[token] /= 10**TOKEN_DECIMALS[chain][token.lower()]

    return res


@timed_cache(60, maxsize=50)
def get_pending_admin_fee(chain: str,
                          address: str,
                          block: Union[int, str] = 'latest') -> int:
    return call_abi(SYN_DATA[chain],
                    'bridge_contract',
                    'getFeeBalance',
                    address,
                    call_args={'block_identifier': block})


def get_pending_admin_fees(chain: str,
                           block: Union[int, str] = 'latest',
                           handle_decimals: bool = False,
                           tokens: List[str] = None) -> Dict[str, float]:
    if tokens is None:
        tokens = get_all_tokens_in_pool(chain)

    res: Dict[str, float] = {}

    if tokens:
        for token in tokens:
            res[token] = get_pending_admin_fee(chain, token, block)

            if handle_decimals:
                res[token] /= 10**TOKEN_DECIMALS[chain][token.lower()]

    return res


def get_admin_and_pending_fees(chain: str,
                               block: Union[int, str] = 'latest',
                               handle_decimals: bool = False,
                               tokens: List[str] = None) -> Dict[str, float]:
    if tokens is None:
        tokens = get_all_tokens_in_pool(chain)

    res: Dict[str, float] = {}
    jobs: List[Greenlet] = []

    for x in [get_admin_fees, get_pending_admin_fees]:
        jobs.append(pool.spawn(x, chain, block, handle_decimals, tokens))

    ret: List[Greenlet] = gevent.joinall(jobs)
    for x in ret:
        res.update(raise_if(x.get(), None))

    return res


def get_chain_validator_gas_fees(
        chain: str) -> Dict[str, Dict[str, Union[str, float]]]:
    # We aggregate validator gas fees on `IN` txs.
    ret = get_all_keys(f'{chain}:bridge:*:IN',
                       client=LOGS_REDIS_URL,
                       index=2,
                       serialize=True)

    res: Dict[str, Dict[str, Union[str, float]]] = defaultdict(dict)

    for k, v in ret.items():
        price = get_historic_price(_chain_to_cgid[chain], k)
        x = v['validator']

        add_to_dict(res[k], 'gas_price', x['gas_price'])
        add_to_dict(res[k], 'transaction_fee', x['gas_paid'])
        add_to_dict(res[k], 'price_usd', x['gas_paid'] * price)
        add_to_dict(res[k], 'tx_count', v['txCount'])

    return res


def get_chain_bridge_fees(chain: str, address: str):
    # We aggregate bridge fees on `IN` txs
    ret = get_all_keys(f'{chain}:bridge:*:{address}:IN',
                       client=LOGS_REDIS_URL,
                       index=2,
                       serialize=True)

    res = defaultdict(dict)

    for k, v in ret.items():
        price = get_historic_price_for_address(chain, address, k)

        res[k] = {
            'volume': v['amount'],
            'price_usd': v['amount'] * price,
            'tx_count': v['txCount'],
        }

    total, total_usd, total_usd_current = create_totals(res,
                                                        chain,
                                                        address,
                                                        is_out=False)

    return {
        'stats': {
            'volume': total,
            'usd': {
                'adjusted': total_usd,
                'current': total_usd_current,
            },
        },
        'data': res,
    }

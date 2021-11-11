#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Dict, Union, List

from syn.utils.contract import get_all_tokens_in_pool, call_abi
from syn.utils.data import SYN_DATA, TOKEN_DECIMALS
from syn.utils.cache import timed_cache
from syn.utils.helpers import raise_if

from gevent.greenlet import Greenlet
from gevent.pool import Pool
import gevent

pool = Pool()


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
    _chain = 'eth' if chain == 'ethereum' else chain

    if tokens is None:
        tokens = get_all_tokens_in_pool(chain)

    res: Dict[str, float] = {}

    if tokens:
        for i, token in enumerate(tokens):
            res[token] = get_admin_fee(chain, i, block)

            if handle_decimals:
                res[token] /= 10**TOKEN_DECIMALS[_chain][token.lower()]

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
    _chain = 'eth' if chain == 'ethereum' else chain

    if tokens is None:
        tokens = get_all_tokens_in_pool(chain)

    res: Dict[str, float] = {}

    if tokens:
        for token in tokens:
            res[token] = get_pending_admin_fee(chain, token, block)

            if handle_decimals:
                res[token] /= 10**TOKEN_DECIMALS[_chain][token.lower()]

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
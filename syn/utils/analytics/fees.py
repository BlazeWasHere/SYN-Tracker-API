#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Dict, Union

from syn.utils.contract import get_all_tokens_in_pool, call_abi
from syn.utils.cache import timed_cache
from syn.utils.data import SYN_DATA


@timed_cache(60, maxsize=50)
def get_admin_fee(chain: str,
                  index: int,
                  block: Union[int, str] = 'latest') -> int:
    return call_abi(SYN_DATA[chain],
                    'metapool_contract',
                    'getAdminBalance',
                    index,
                    call_args={'block_identifier': block})


@timed_cache(60)
def get_admin_fees(chain: str,
                   block: Union[int, str] = 'latest') -> Dict[str, int]:
    tokens = get_all_tokens_in_pool(chain)
    res: Dict[str, int] = {}

    for i, token in enumerate(tokens):
        res[token] = get_admin_fee(chain, i, block)

    return res
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Union, Dict

from syn.utils.contract import call_abi
from syn.utils.cache import timed_cache
from syn.utils.data import SYN_DATA


@timed_cache(60, maxsize=50)
def get_virtual_price(chain: str,
                      block: Union[int, str] = 'latest',
                      func: str = 'metapool_contract') -> Dict[str, float]:
    ret = call_abi(SYN_DATA[chain],
                   func,
                   'getVirtualPrice',
                   call_args={'block_identifier': block})

    # 18 Decimals.
    return {chain: ret / 10**18}

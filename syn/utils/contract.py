#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Optional, List, Any

import web3.exceptions

from .data import SYN_DATA, MAX_UINT8
from .cache import timed_cache


# TODO(blaze): better type hints.
def call_abi(data, key: str, func_name: str, *args, **kwargs) -> Any:
    call_args = kwargs.pop('call_args', {})
    return getattr(data[key].functions, func_name)(*args,
                                                   **kwargs).call(**call_args)


@timed_cache(60)
def get_all_tokens_in_pool(
    chain: str,
    max_index: Optional[int] = None,
) -> List[str]:
    """
    Get all tokens by calling `getToken` by iterating from 0 till a
    contract error or `max_index` and implicitly sorted by index.

    Args:
        chain (str): the EVM chain
        max_index (Optional[int], optional): max index to iterate to. 
            Defaults to None.

    Returns:
        List[str]: list of token addresses
    """

    assert (chain in SYN_DATA)

    data = SYN_DATA[chain]
    res: List[str] = []

    for i in range(max_index or MAX_UINT8):
        try:
            res.append(call_abi(data, 'pool_contract', 'getToken', i))
        except (web3.exceptions.ContractLogicError,
                web3.exceptions.BadFunctionCallOutput):
            # Out of range.
            break

    return res

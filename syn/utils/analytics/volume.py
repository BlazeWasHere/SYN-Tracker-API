#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Callable, Dict, List, Literal

import dateutil.parser

from syn.utils.wrappa.moralis import Moralis
from syn.utils.data import MORALIS_APIKEY
from syn.utils.cache import timed_cache

if MORALIS_APIKEY is None:
    raise TypeError('`MORALIS_APIKEY` is not set')

moralis = Moralis(MORALIS_APIKEY)


def _always_true(*args, **kwargs) -> Literal[True]:
    return True


@timed_cache(360)
def get_chain_volume(
    address: str,
    chain: str,
    filter: Callable[[Dict[str, str]],
                     bool] = _always_true) -> Dict[str, float]:
    # TODO(blaze): Cache past days volume, after all they dont change.
    data = moralis.erc20_transfers(address, chain)
    res: Dict[str, float] = {}

    for x in data:
        if filter(x):
            key = str(dateutil.parser.parse(x['block_timestamp']).date())

            if key not in res:
                # TODO(blaze): dont hardcode the decimals
                res.update({key: int(x['value']) / 1e18})
            else:
                # Ditto.
                res[key] += int(x['value']) / 1e18

    return res

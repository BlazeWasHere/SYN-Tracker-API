#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Dict, DefaultDict, List, Union
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from syn.utils.price import get_historic_price_for_address
from syn.utils.helpers import get_all_keys
from syn.utils.data import LOGS_REDIS_URL


def chart_chain_bridge_volume(
    chain: str,
    direction: str = 'IN',
) -> DefaultDict[str, List[Dict[str, Union[int, float]]]]:
    res = defaultdict(list)

    if direction not in ['IN', 'OUT']:
        raise TypeError(f'expected direction as IN or OUT got {direction!r}')

    ret: Dict[str, Dict[str, str]] = get_all_keys(
        f'{chain}:bridge:*:{direction}',
        client=LOGS_REDIS_URL,
        index=False,
        serialize=True,
    )

    for k, v in ret.items():
        _, _, date, address, _ = k.split(':')

        price = get_historic_price_for_address(chain, address, date)
        volume = Decimal(v['amount'])

        res[address].append({
            'date': datetime.fromisoformat(date).timestamp(),
            'price': price,
            'tx_count': v['txCount'],
            'volume': volume,
        })

    return res

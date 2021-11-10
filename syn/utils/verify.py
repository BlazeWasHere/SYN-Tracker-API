#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Literal, Union
from datetime import datetime


def isdigit(str: str) -> bool:
    """
    Same as `str.isdigit()` except it supports negative numbers (x < 0)
    """
    return str.isdigit() or (str.startswith('-') and str[1:].isdigit())


def is_sane_date(date: datetime) -> Union[Literal[True], str]:
    now = datetime.now()

    if date > now:
        return f'{date} is in the future'
    elif date < datetime(year=2021, month=11, day=6):
        # New pools were created post failed exploit. ref:
        # https://synapseprotocol.medium.com/11-06-2021-post-mortem-of-synapse-metapool-exploit-3003b4df4ef4
        return f'the pools weren not created at {date}'

    return True

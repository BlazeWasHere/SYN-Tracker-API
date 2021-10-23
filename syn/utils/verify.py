#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""


def isdigit(str: str) -> bool:
    """
    Same as `str.isdigit()` except it supports negative numbers (x < 0)
    """
    return str.isdigit() or (str.startswith('-') and str[1:].isdigit())

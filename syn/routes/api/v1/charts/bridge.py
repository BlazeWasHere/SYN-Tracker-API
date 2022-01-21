#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from flask import Blueprint, jsonify

from syn.utils.charts.bridge import chart_chain_bridge_volume
from syn.utils.data import cache

charts_bridge_bp = Blueprint('charts_bridge_bp', __name__)
# 15m
TIMEOUT = 15 * 60


@charts_bridge_bp.route('/<chain:chain>', methods=['GET'])
@cache.cached(timeout=TIMEOUT)
def chain_direction_chart(chain: str):
    return jsonify(chart_chain_bridge_volume(chain))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from collections import defaultdict
from datetime import datetime

from flask import Blueprint, jsonify
import simplejson as json
from web3 import Web3

from syn.utils.data import LOGS_REDIS_URL, SYN_DATA, cache, _forced_update, \
    DEFAULT_TIMEOUT
from syn.utils.helpers import get_all_keys

utils_bp = Blueprint('utils_bp', __name__)


# Something a bit more internal, but useful for tracking sync status because
# we launch `update_getlogs` as a daemon now.
@utils_bp.route('/syncing', methods=['GET'])
def syncing():
    ret = get_all_keys('*MAX_BLOCK_STORED',
                       serialize=True,
                       index=0,
                       client=LOGS_REDIS_URL,
                       use_max_of_duped_keys=True)
    res = defaultdict(dict)

    for chain, v in ret.items():
        w3: Web3 = SYN_DATA[chain]['w3']
        res[chain] = {'current': v, 'blockheight': w3.eth.block_number}

    return jsonify(res)


@utils_bp.route('/date2block/<chain:chain>/<date:date>', methods=['GET'])
@cache.cached(timeout=DEFAULT_TIMEOUT, forced_update=_forced_update)
def chain_date_to_block(chain: str, date: datetime):
    _date = str(date.date())

    ret = LOGS_REDIS_URL.get(f'{chain}:date2block:{_date}')
    if ret is not None:
        ret = json.loads(ret)

    return jsonify({_date: ret})

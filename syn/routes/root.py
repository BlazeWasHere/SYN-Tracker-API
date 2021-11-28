#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from collections import defaultdict
import json
import os

from flask import Blueprint, jsonify
from web3 import Web3
import gevent

from syn.utils.data import LOGS_REDIS_URL, SYN_DATA
from syn.utils.helpers import get_all_keys

# Get parent (root) dir.
_path = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
openapi_folder = os.path.join(_path, 'docs', 'openapi')
template_folder = os.path.join(_path, 'public')
root_bp = Blueprint('root_bp', __name__, static_folder=template_folder)

with open(os.path.join(openapi_folder, 'specification.json')) as f:
    OPENAPI_DATA = json.load(f)


@root_bp.route('/')
def index():
    return root_bp.send_static_file('index.html')


@root_bp.route('/openapi.json')
def openapi():
    return jsonify(OPENAPI_DATA)


# Something a bit more internal, but useful for tracking sync status because
# we launch `update_getlogs` as a daemon now.
@root_bp.route('/syncing')
def syncing():
    ret = get_all_keys('*MAX_BLOCK_STORED',
                       serialize=True,
                       index=0,
                       client=LOGS_REDIS_URL)
    res = defaultdict(dict)

    for chain, v in ret.items():
        w3: Web3 = SYN_DATA[chain]['w3']
        res[chain] = {'current': v, 'blockheight': w3.eth.block_number}

    return jsonify(res)

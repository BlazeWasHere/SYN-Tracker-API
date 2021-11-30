#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from gevent import monkey
import gevent

# Monkey patch stuff.
monkey.patch_all()

from syn.utils.data import SYN_DATA
from web3._utils import request
from math import log2
import lru

# Get the next ^2 that is greater than len(SYN_DATA.keys()) so we can make
# the cache size greater than the amount of chains we support.
n = 1 << int(log2(len(SYN_DATA.keys()))) + 1

b = request._session_cache.get_size()
request._session_cache.set_size(n)
c = request._session_cache.get_size()
assert b != c, '_session_cache size did not change'
assert c == n, 'new _session_cache size is not what we set it to'

import simplejson as json
from flask import Flask
import redis_lock

from syn.cron import update_caches, update_getlogs, update_getlogs_pool
from syn.utils.data import cache, SCHEDULER_CONFIG, schedular, \
    MESSAGE_QUEUE_REDIS

import os


def _first_run() -> None:
    lock = redis_lock.Lock(MESSAGE_QUEUE_REDIS,
                           "first_run",
                           id=str(os.getpid()))

    with lock:
        print(f'pid({os.getpid()}), acquired the lock')
        assert lock.locked()

        update_getlogs_pool()
        update_getlogs()
        update_caches()

        # We want schedular to start AFTER.
        schedular.start()


gevent.spawn(_first_run)


def init() -> Flask:
    app = Flask(__name__)
    app.json_encoder = json.JSONEncoder  # type: ignore
    app.json_decoder = json.JSONDecoder  # type: ignore

    from .utils.converters import register_converter
    register_converter(app, 'chain')
    register_converter(app, 'date')

    from .routes.api.v1.analytics.emissions import emissions_bp
    from .routes.api.v1.analytics.treasury import treasury_bp
    from .routes.api.v1.analytics.volume import volume_bp
    from .routes.api.v1.analytics.pools import pools_bp
    from .routes.api.v1.analytics.fees import fees_bp
    from .routes.api.v1.utils import utils_bp
    from .routes.api.v1.circ import circ_bp
    from .routes.api.v1.mcap import mcap_bp
    from .routes.root import root_bp

    app.register_blueprint(root_bp)
    app.register_blueprint(circ_bp, url_prefix='/api/v1/circ')
    app.register_blueprint(mcap_bp, url_prefix='/api/v1/mcap')
    app.register_blueprint(utils_bp, url_prefix='/api/v1/utils')
    app.register_blueprint(fees_bp, url_prefix='/api/v1/analytics/fees')
    app.register_blueprint(pools_bp, url_prefix='/api/v1/analytics/pools')
    app.register_blueprint(volume_bp, url_prefix='/api/v1/analytics/volume')
    app.register_blueprint(treasury_bp,
                           url_prefix='/api/v1/analytics/treasury')
    app.register_blueprint(emissions_bp,
                           url_prefix='/api/v1/analytics/emissions')

    app.config.from_mapping(SCHEDULER_CONFIG)
    schedular.init_app(app)
    cache.init_app(app)

    return app

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Tuple, List

from gevent import monkey, Greenlet
import gevent

monkey.patch_all()

from flask_socketio import SocketIO
from flask import Flask

from syn.utils.data import cache, SCHEDULER_CONFIG, schedular, POPULATE_CACHE, \
    SYN_DATA, MESSAGE_QUEUE_REDIS_URL


def init(debug: bool = False) -> Tuple[Flask, SocketIO]:
    app = Flask(__name__)

    from .utils.converters import register_converter
    register_converter(app, 'date')

    app.socketio = SocketIO(  # type: ignore
        app,
        logger=debug,
        engineio_logger=debug,
        asnyc_mode='gevent',
        message_queue=MESSAGE_QUEUE_REDIS_URL)

    from .routes.api.v1.analytics.treasury import treasury_bp
    from .routes.api.v1.analytics.volume import volume_bp
    from .routes.api.v1.analytics.pools import pools_bp
    from .routes.api.v1.analytics.fees import fees_bp
    from .routes.api.v1.circ import circ_bp
    from .routes.api.v1.mcap import mcap_bp
    from .routes.root import root_bp

    app.register_blueprint(root_bp)
    app.register_blueprint(circ_bp, url_prefix='/api/v1/circ')
    app.register_blueprint(mcap_bp, url_prefix='/api/v1/mcap')
    app.register_blueprint(fees_bp, url_prefix='/api/v1/analytics/fees')
    app.register_blueprint(pools_bp, url_prefix='/api/v1/analytics/pools')
    app.register_blueprint(volume_bp, url_prefix='/api/v1/analytics/volume')
    app.register_blueprint(treasury_bp,
                           url_prefix='/api/v1/analytics/treasury')

    if POPULATE_CACHE:
        from .utils.wrappa.rpc import get_logs

        jobs: List[Greenlet] = []

        for chain in SYN_DATA:
            if chain in ['harmony', 'bsc', 'polygon']:
                jobs.append(gevent.spawn(get_logs, chain, max_blocks=1024))
            else:
                jobs.append(gevent.spawn(get_logs, chain))

    from .cron import update_caches

    app.config.from_mapping(SCHEDULER_CONFIG)
    schedular.init_app(app)
    cache.init_app(app)
    # First run.
    update_caches()
    schedular.start()

    with app.app_context():
        from .routes.api.v1.explorer import ws

    ws.start()

    if POPULATE_CACHE:
        gevent.joinall(jobs)  # type: ignore

    return app, app.socketio  # type: ignore

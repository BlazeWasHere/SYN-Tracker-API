#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from gevent import monkey

monkey.patch_all()

from flask import Flask


def init() -> Flask:
    app = Flask(__name__)

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

    from .utils.data import cache, SCHEDULER_CONFIG, schedular
    from .cron import update_caches

    app.config.from_mapping(SCHEDULER_CONFIG)
    schedular.init_app(app)
    cache.init_app(app)
    # First run.
    update_caches()
    schedular.start()

    return app

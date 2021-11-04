#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

import os
import time

from redis import Redis
import redis_lock

from syn.utils.data import schedular, CACHE_FORCED_UPDATE

routes = [
    '/api/v1/analytics/volume/ethereum/filter/nusd',
    '/api/v1/analytics/volume/ethereum/filter/syn',
    '/api/v1/analytics/volume/ethereum/filter/high',
    '/api/v1/analytics/volume/ethereum/filter/dog',
    '/api/v1/analytics/volume/ethereum/filter/usdt',
    '/api/v1/analytics/volume/ethereum/filter/usdc',
    '/api/v1/analytics/volume/ethereum/filter/dai',
    '/api/v1/analytics/volume/ethereum',
    '/api/v1/analytics/volume/bsc/filter/nusd',
    '/api/v1/analytics/volume/bsc/filter/syn',
    '/api/v1/analytics/volume/bsc/filter/high',
    '/api/v1/analytics/volume/bsc/filter/dog',
    '/api/v1/analytics/volume/bsc',
    '/api/v1/analytics/volume/polygon/filter/syn',
    '/api/v1/analytics/volume/polygon/filter/nusd',
    '/api/v1/analytics/volume/polygon',
    '/api/v1/analytics/volume/metapool/bsc',
    '/api/v1/analytics/volume/metapool/avalanche',
    '/api/v1/analytics/volume/metapool/polygon',
    '/api/v1/analytics/volume/metapool/arbitrum',
    '/api/v1/analytics/volume/metapool/fantom',
]


@schedular.task("cron", id="update_caches", minute="*/15")
def update_caches():
    global CACHE_FORCED_UPDATE

    r: Redis = schedular._scheduler._jobstores['default'].redis
    lock = redis_lock.Lock(r, 'CRON_UPDATE_CACHES_LOCK', id=str(os.getpid()))

    # Some logic to prevent multiple cron jobs running when we are scaling the
    # app with more workers.
    if not lock.acquire(blocking=False):
        print(f'It seems pid({lock.get_owner_id()}) got to the lock first. '
              'Skipping the job...')
        return

    assert lock.locked()

    start = time.time()
    print(f'[{start}] Cron job start.')

    # TODO(blaze): This doesn't actually work in the cache func.
    CACHE_FORCED_UPDATE = True

    with schedular.app.test_client() as c:  # type: ignore
        for route in routes:
            print(f'Updating cache for route ~> {route}')
            c.get(route)

    CACHE_FORCED_UPDATE = False
    print(f'Cron job done. Elapsed: {round(time.time() - start, 2)}s')
    lock.release()
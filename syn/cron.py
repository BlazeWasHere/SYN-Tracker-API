#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from contextlib import contextmanager
from typing import Generator
from functools import wraps
import time
import os

from syn.utils.helpers import dispatch_get_logs, worker_assert_lock
from syn.utils.data import schedular, MESSAGE_QUEUE_REDIS
from syn.utils.analytics.pool import pool_callback
from syn.utils.wrappa.rpc import bridge_callback

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
    '/api/v1/analytics/pools/metapool/price/virtual',
    '/api/v1/analytics/pools/basepool/price/virtual',
    '/api/v1/analytics/pools/metapool/price/virtual/arbitrum',
    '/api/v1/analytics/pools/metapool/price/virtual/bsc',
    '/api/v1/analytics/pools/metapool/price/virtual/polygon',
    '/api/v1/analytics/pools/metapool/price/virtual/avalanche',
    '/api/v1/analytics/pools/metapool/price/virtual/harmony',
    '/api/v1/analytics/pools/metapool/price/virtual/fantom',
    '/api/v1/analytics/pools/basepool/price/virtual/arbitrum',
    '/api/v1/analytics/pools/basepool/price/virtual/bsc',
    '/api/v1/analytics/pools/basepool/price/virtual/polygon',
    '/api/v1/analytics/pools/basepool/price/virtual/avalanche',
    '/api/v1/analytics/pools/basepool/price/virtual/harmony',
    '/api/v1/analytics/pools/basepool/price/virtual/fantom',
]


def acquire_lock(name: str):
    @contextmanager
    def ctx_lock() -> Generator[None, None, None]:
        lock = worker_assert_lock(MESSAGE_QUEUE_REDIS, name, str(os.getpid()))
        assert lock != False, 'failed to acquire lock'
        print(f'worker({os.getpid()}), acquired the lock')

        try:
            yield None
        finally:
            lock.release()

    def _decorator(fn):
        @wraps(fn)
        def _wrapped(*args, **kwargs):
            with ctx_lock():
                return fn(*args, **kwargs)

        return _wrapped

    return _decorator


@schedular.task("interval", id="update_caches", minutes=15, max_instances=1)
@acquire_lock('update_caches')
def update_caches():
    start = time.time()
    print(f'(0) [{start}] Cron job start.')

    with schedular.app.test_client() as c:  # type: ignore
        for route in routes:
            print(f'(0) Updating cache for route ~> {route}')
            c.get(route)

    print(f'(0) Cron job done. Elapsed: {time.time() - start:.2f}s')


@schedular.task("interval", id="update_getlogs", hours=1, max_instances=1)
@acquire_lock('update_getlogs')
def update_getlogs():
    start = time.time()
    print(f'(2) [{start}] Cron job start.')

    dispatch_get_logs(bridge_callback)

    print(f'(2) Cron job done. Elapsed: {time.time() - start:.2f}s')


@schedular.task("interval", id="update_getlogs_pool", hours=1, max_instances=1)
@acquire_lock('update_getlogs_pool')
def update_getlogs_pool():
    from syn.utils.analytics.pool import TOPICS

    start = time.time()
    print(f'(3) [{start}] Cron job start.')

    dispatch_get_logs(pool_callback,
                      topics=list(TOPICS),
                      key_namespace='pool',
                      address_key=-1)

    print(f'(3) Cron job done. Elapsed: {time.time() - start:.2f}s')

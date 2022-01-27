#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from contextlib import contextmanager
from datetime import datetime
from typing import Generator
from functools import wraps
import traceback
import time
import os

import requests

from syn.utils.helpers import dispatch_get_logs, worker_assert_lock
from syn.utils.data import schedular, MESSAGE_QUEUE_REDIS, REDIS, \
    COINGECKO_HISTORIC_URL
from syn.utils.analytics.pool import pool_callback
from syn.utils.cache import _serialize_args_to_str
from syn.utils.wrappa.rpc import bridge_callback
from syn.utils.price import CoingeckoIDS


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


@schedular.task("cron", id="update_prices", hour=0, max_instances=1)
@acquire_lock('update_prices')
def update_prices():
    start = time.time()
    print(f'(0) [{start}] Cron job start.')
    date = datetime.now().strftime('%d-%m-%Y')

    for x in CoingeckoIDS:
        _key = _serialize_args_to_str(x, date)
        keys = [_key, f'{_key}:usd']

        for key in keys:
            if REDIS.get(key) is None:
                try:
                    r = requests.get(
                        COINGECKO_HISTORIC_URL.format(x.value, date))
                    r = r.json()

                    REDIS.setnx(_key, r['market_data']['current_price']['usd'])
                    print(REDIS.get(_key))
                except Exception:
                    traceback.print_exc()
                    print(key, r)
            else:
                print(f'{key} has a value??')

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

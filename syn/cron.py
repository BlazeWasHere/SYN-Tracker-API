#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Literal, Union
from datetime import datetime
import time
import os

from redis import Redis
import redis_lock

from syn.routes.api.v1.analytics.pools import metapools, basepools
from syn.utils.data import REDIS, schedular, MORALIS_APIKEY
from syn.utils.contract import get_virtual_price
from syn.utils.wrappa.rpc import bridge_callback
from syn.utils.helpers import dispatch_get_logs
from syn.utils.wrappa.moralis import Moralis

moralis = Moralis(MORALIS_APIKEY)

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


def lock_ownership(r: Redis, name: str,
                   _id: int) -> Union[Literal[False], redis_lock.Lock]:
    lock = redis_lock.Lock(r, name, id=str(os.getpid()))

    # Some logic to prevent multiple cron jobs running when we are scaling the
    # app with more workers.
    if not lock.acquire(blocking=False):
        print(f'({_id}) It seems pid({lock.get_owner_id()}) got to the lock '
              'first. Skipping the job...')
        return False

    if not lock.locked():
        return False

    return lock


@schedular.task("cron", id="update_caches", minute="*/15")
def update_caches():
    r: Redis = schedular._scheduler._jobstores['default'].redis
    if not (lock := lock_ownership(r, 'CRON_UPDATE_CACHES_LOCK', 0)):
        return

    start = time.time()
    print(f'(0) [{start}] Cron job start.')

    with lock:
        with schedular.app.test_client() as c:  # type: ignore
            for route in routes:
                print(f'(0) Updating cache for route ~> {route}')
                c.get(route)

    print(f'(0) Cron job done. Elapsed: {time.time() - start:.2f}s')


@schedular.task("interval", id="update_getlogs", hours=1)
def update_getlogs():
    r: Redis = schedular._scheduler._jobstores['default'].redis
    if not (lock := lock_ownership(r, 'CRON_UPDATE_GETLOGS_LOCK', 2)):
        return

    start = time.time()
    print(f'(2) [{start}] Cron job start.')

    with lock:
        dispatch_get_logs(bridge_callback, join_all=True)

    print(f'(2) Cron job done. Elapsed: {time.time() - start:.2f}s')


# Run at 00:01, it is sufficient enough to wait for the first block of the current day.
@schedular.task("cron", id="set_today_vp", hour=0, minute=1)
def set_virtual_price():
    r: Redis = schedular._scheduler._jobstores['default'].redis

    if not (lock := lock_ownership(r, 'CRON_UPDATE_VP_LOCK', 2)):
        return

    start = time.time()
    print(f'(1) [{start}] Cron job start.')

    date = str(datetime.now().date())
    ret = moralis.date_to_block(date)

    for chain in metapools:
        vp = get_virtual_price(chain, block=ret['block'])
        REDIS.set(f'metapool:{chain}:vp:{date}', vp[chain])

    for chain in basepools:
        vp = get_virtual_price(chain,
                               block=ret['block'],
                               func='basepool_contract')
        REDIS.set(f'basepool:{chain}:vp:{date}', vp[chain])

    print(f'(1) Cron job done. Elapsed: {time.time() - start:.2f}s')
    lock.release()
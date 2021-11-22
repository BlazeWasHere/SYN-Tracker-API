#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

import time

from syn.utils.data import schedular, MORALIS_APIKEY
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


@schedular.task("cron", id="update_caches", minute="*/15", max_instances=1)
def update_caches():
    start = time.time()
    print(f'(0) [{start}] Cron job start.')

    with schedular.app.test_client() as c:  # type: ignore
        for route in routes:
            print(f'(0) Updating cache for route ~> {route}')
            c.get(route)

    print(f'(0) Cron job done. Elapsed: {time.time() - start:.2f}s')


@schedular.task("interval", id="update_getlogs", hours=1, max_instances=1)
def update_getlogs():
    start = time.time()
    print(f'(2) [{start}] Cron job start.')

    dispatch_get_logs(bridge_callback, join_all=True)

    print(f'(2) Cron job done. Elapsed: {time.time() - start:.2f}s')

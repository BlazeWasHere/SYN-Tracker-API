#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from contextlib import contextmanager
from datetime import date, datetime
from typing import Generator
from functools import wraps
from decimal import Decimal
import traceback
import time
import os

import simplejson as json
from web3 import Web3
import requests

from syn.utils.data import (LOGS_REDIS_URL, schedular, MESSAGE_QUEUE_REDIS,
                            REDIS, COINGECKO_HISTORIC_URL, SYN_DATA)
from syn.utils.helpers import dispatch_get_logs, worker_assert_lock, date2block
from syn.utils.analytics.pool import pool_callback
from syn.utils.cache import _serialize_args_to_str
from syn.utils.wrappa.rpc import bridge_callback
from syn.utils.contract import get_balance_of
from syn.utils.price import CoingeckoIDS, get_historic_price


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


def get_price_cg(_id: str, date: str) -> Decimal:
    time.sleep(1)
    r = requests.get(COINGECKO_HISTORIC_URL.format(_id, date))
    return r.json(use_decimal=True)['market_data']['current_price']['usd']


def get_price_xjewel(_date: date) -> Decimal:
    chain = 'dfk'
    w3 = SYN_DATA[chain]['w3']

    key = f'dfk:logs:{SYN_DATA[chain]["bridge"]}:MAX_BLOCK_STORED'
    lp_contract = "0x6AC38A4C112F125eac0eBDbaDBed0BC8F4575d0d"
    tokens = [
        "0xCCb93dABD71c8Dad03Fc4CE5559dC3D89F67a260",  # WJEWEL
        "0x77f2656d04E158f915bC22f07B779D94c1DC47Ff",  # xJEWEL
    ]

    # Different logic if date is today as we cannot assume `update_getlogs`
    # has ran before this function and thus cannot assume `date2block`
    # will return a valid result.
    if _date == date.today():
        block = LOGS_REDIS_URL.get(key)
        assert block, f'failed to find block: {_date} dfk'
        block = int(block)
    else:
        block = date2block(chain, _date)
        assert block, f'failed to find block: {_date} dfk'
        block = block['block']

    t0bal = get_balance_of(w3, tokens[0], lp_contract, 18, block)
    t1bal = get_balance_of(w3, tokens[1], lp_contract, 18, block)

    date_cg = _date.strftime('%d-%m-%Y')
    jewel_price = get_historic_price(CoingeckoIDS.JEWEL, date_cg)

    return jewel_price * t0bal / t1bal


def get_price(_id: str, date: date) -> Decimal:
    CUSTOM_PRICE_FUNCS = {
        'custom-xjewel': get_price_xjewel,
    }

    if _id in CUSTOM_PRICE_FUNCS:
        return CUSTOM_PRICE_FUNCS[_id](date)

    return get_price_cg(_id, date.strftime('%d-%m-%Y'))


@schedular.task("cron", id="update_prices", hour=0, minute=10, max_instances=1)
@acquire_lock('update_prices')
def update_prices():
    start = time.time()
    print(f'(0) [{start}] Cron job start.')

    _now = datetime.now()
    date = _now.strftime('%Y-%m-%d')
    date_cg = _now.date()

    for x in CoingeckoIDS:
        _key = _serialize_args_to_str(x, date)
        keys = [_key, f'{_key}:usd']

        for key in keys:
            if REDIS.get(key) is None:
                try:
                    REDIS.setnx(key, json.dumps(get_price(x.value, date_cg)))
                except Exception as e:
                    MESSAGE_QUEUE_REDIS.sadd('prices:missing', key)

                    if not type(e) == KeyError:
                        traceback.print_exc()
                        print(key)
            else:
                print(f'{key} has a value??')

    print(f'(0) Cron job done. Elapsed: {time.time() - start:.2f}s')


@schedular.task("interval",
                id="update_prices_missing",
                hours=1,
                max_instances=1)
@acquire_lock('update_prices_missing')
def update_prices_missing():
    start = time.time()
    print(f'(1) [{start}] Cron job start.')

    keys = MESSAGE_QUEUE_REDIS.smembers('prices:missing')

    for key in keys:
        # TODO(blaze): remove now or later?
        MESSAGE_QUEUE_REDIS.srem('prices:missing', 1, key)

        # Check if price is actually missing
        if (_ := REDIS.get(key)) is None or _ == '0':
            if (key.endswith(':usd')):
                if (data := REDIS.get(key.replace(':usd', ''))) is not None:
                    REDIS.setnx(key, data)
                    continue
            else:
                if (data := REDIS.get(f'{key}:usd')) is not None:
                    REDIS.setnx(key, data)
                    continue

            x = key.split(':')
            _id, date = x[0], x[1]
            date = datetime.fromisoformat(date).date()

            try:
                REDIS.setnx(key, json.dumps(get_price(_id, date)))
            except Exception as e:
                MESSAGE_QUEUE_REDIS.sadd('prices:missing', key)

                if not type(e) == KeyError:
                    traceback.print_exc()
                    print(key)

    print(f'(1) Cron job done. Elapsed: {time.time() - start:.2f}s')


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

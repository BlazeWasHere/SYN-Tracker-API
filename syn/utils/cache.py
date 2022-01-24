#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Callable, Optional, Union
from functools import lru_cache, wraps
from datetime import timedelta
import time

from flask_caching.backends import SimpleCache
import simplejson as json

from .data import REDIS

_redis_cache = SimpleCache()


# Gotta love SO: https://stackoverflow.com/a/63674816
def timed_cache(max_age, maxsize=5, typed=False):
    """
    Least-recently-used cache decorator with time-based cache invalidation.

    Args:
        max_age: Time to live for cached results (in seconds).
        maxsize: Maximum cache size (see `functools.lru_cache`).
        typed: Cache on distinct input types (see `functools.lru_cache`).
    """
    def _decorator(fn):
        @lru_cache(maxsize=maxsize, typed=typed)
        def _new(*args, __time_salt, **kwargs):
            return fn(*args, **kwargs)

        @wraps(fn)
        def _wrapped(*args, **kwargs):
            return _new(*args,
                        **kwargs,
                        __time_salt=round(time.time() / max_age))

        return _wrapped

    return _decorator


def _serialize_args_to_str(*args, **kwargs) -> str:
    from .helpers import flatten_dict
    from .price import CoingeckoIDS

    res = []

    if kwargs.pop('is_class', False):
        x = list(args)
        x.pop(0)
        args = tuple(x)

    for arg in args:
        if isinstance(arg, CoingeckoIDS):
            res.append(arg.value)
        else:
            res.append(str(arg))

    return ':'.join(res) + flatten_dict(kwargs)


def redis_cache(key: Optional[Callable[..., str]] = None,
                expires_at: Optional[Union[int, timedelta]] = None,
                filter: Callable[..., bool] = lambda *args, **kwargs: True,
                is_class: bool = False):
    """
    Fetch `key` from `REDIS` else run the function and store the response
    as `key` for later (cache) usage.

    Args:
        expires_at (Optional[int], optional): time `key` should expire. Defaults to None.
    """
    def _decorator(fn):
        @wraps(fn)
        def _wrapped(*args, **kwargs):
            if key is None:
                _key = _serialize_args_to_str(*args,
                                              **kwargs,
                                              is_class=is_class)
            else:
                _key = key(*args, **kwargs, is_class=is_class)

            # Check internal cache.
            if (data := _redis_cache.get(_key)) is not None:
                return data

            # Check redis cache.
            if (data := REDIS.get(_key)) is not None:
                if isinstance(data, str):
                    try:
                        data = json.loads(data, use_decimal=True)
                    except json.JSONDecodeError:
                        pass

                # 5m
                _redis_cache.add(_key, data, timeout=60 * 5)

                return data

            # Missed, update cache.
            res = fn(*args, **kwargs)

            if filter(res):
                if not isinstance(res, (str, bytes, float, int)):
                    res = json.dumps(res)

                # 5m
                _redis_cache.add(_key, res, timeout=60 * 5)
                REDIS.set(_key, res, expires_at)

            return res

        return _wrapped

    return _decorator
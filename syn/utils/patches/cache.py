#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Callable, Dict, Optional
from time import time
import traceback
import functools
import hashlib
import inspect
import logging

from flask_caching import Cache, wants_args
from flask import request, url_for

logger = logging.getLogger('flask_caching')
# {
#    cache_key: expiry
# }
_cache: Dict[str, float] = {}


class PatchedCache(Cache):
    def cached(
        self: Cache,
        timeout: int = 60 * 60,  # 1 hour default.
        key_prefix: str = "view/%s",
        unless: Optional[Callable] = None,
        forced_update: Optional[Callable] = None,
        response_filter: Optional[Callable] = None,
        query_string: bool = False,
        hash_method: Callable = hashlib.md5,
        cache_none: bool = False,
        make_cache_key: Optional[Callable] = None,
        source_check: Optional[bool] = None,
    ) -> Callable:
        def decorator(f):
            @functools.wraps(f)
            def decorated_function(*args, **kwargs):
                print(self.cache, _cache, time())

                #: Bypass the cache entirely.
                if self._bypass_cache(unless, f, *args, **kwargs):
                    return f(*args, **kwargs)

                assert timeout > 0
                nonlocal source_check
                if source_check is None:
                    source_check = self.source_check

                try:
                    if make_cache_key is not None and callable(make_cache_key):
                        cache_key = make_cache_key(*args, **kwargs)
                    else:
                        cache_key = _make_cache_key(args,
                                                    kwargs,
                                                    use_request=True)
                    if (callable(forced_update)
                            and (forced_update(*args, **kwargs) if wants_args(
                                forced_update) else forced_update()) is True):
                        rv = None
                        found = False
                    else:
                        rv = self.cache.get(cache_key)
                        found = True

                        # If the value returned by cache.get() is None, it
                        # might be because the key is not found in the cache
                        # or because the cached value is actually None
                        if rv is None:
                            # If we're sure we don't need to cache None values
                            # (cache_none=False), don't bother checking for
                            # key existence, as it can lead to false positives
                            # if a concurrent call already cached the
                            # key between steps. This would cause us to
                            # return None when we shouldn't
                            if not cache_none:
                                found = False
                            else:
                                found = self.cache.has(cache_key)
                except Exception:
                    if self.app.debug:
                        raise
                    logger.exception(
                        "Exception possibly due to cache backend.")
                    return f(*args, **kwargs)

                if not found:
                    try:
                        rv = f(*args, **kwargs)
                    except Exception:
                        traceback.print_exc()
                        # Do NOT update the cache, serve the old data even if stale.
                        rv = None

                    if response_filter is None or response_filter(rv):
                        if rv is None:
                            # Hopefully this actually returns something.
                            return self.cache.get(cache_key)

                if (rv is not None and
                    (cache_key in _cache and _cache[cache_key] < time())
                        or cache_key not in _cache):
                    ret = self.cache.set(
                        cache_key,
                        rv,
                        # Do not timeout/delete items in the cache.
                        timeout=None,
                    )

                    if ret:
                        expiry = time() + timeout
                        _cache[cache_key] = expiry
                    else:
                        logger.critical(
                            f'Got {ret!r} expected True when setting ',
                            f'cache for key {cache_key} and value {rv}',
                        )

                return rv

            def default_make_cache_key(*args, **kwargs):
                # Convert non-keyword arguments (which is the way
                # `make_cache_key` expects them) to keyword arguments
                # (the way `url_for` expects them)
                argspec_args = inspect.getfullargspec(f).args

                for arg_name, arg in zip(argspec_args, args):
                    kwargs[arg_name] = arg

                return _make_cache_key(args, kwargs, use_request=False)

            def _make_cache_key_query_string():
                """
                Create consistent keys for query string arguments.

                Produces the same cache key regardless of argument order, e.g.,
                both `?limit=10&offset=20` and `?offset=20&limit=10` will
                always produce the same exact cache key.

                If func is provided and is callable it will be used to hash
                the function's source code and include it in the cache key.
                This will only be done is source_check is True.
                """

                # Create a tuple of (key, value) pairs, where the key is the
                # argument name and the value is its respective value. Order
                # this tuple by key. Doing this ensures the cache key created
                # is always the same for query string args whose keys/values
                # are the same, regardless of the order in which they are
                # provided.

                args_as_sorted_tuple = tuple(
                    sorted((pair for pair in request.args.items(multi=True))))
                # ... now hash the sorted (key, value) tuple so it can be
                # used as a key for cache. Turn them into bytes so that the
                # hash function will accept them
                args_as_bytes = str(args_as_sorted_tuple).encode()
                cache_hash = hash_method(args_as_bytes)

                # Use the source code if source_check is True and update the
                # cache_hash before generating the hashing and using it in
                # cache_key
                if source_check and callable(f):
                    func_source_code = inspect.getsource(f)
                    cache_hash.update(func_source_code.encode("utf-8"))

                cache_hash = str(cache_hash.hexdigest())

                cache_key = request.path + cache_hash

                return cache_key

            def _make_cache_key(args, kwargs, use_request):
                if query_string:
                    return _make_cache_key_query_string()
                else:
                    if callable(key_prefix):
                        cache_key = key_prefix()
                    elif "%s" in key_prefix:
                        if use_request:
                            cache_key = key_prefix % request.path
                        else:
                            cache_key = key_prefix % url_for(
                                f.__name__, **kwargs)
                    else:
                        cache_key = key_prefix

                if source_check and callable(f):
                    func_source_code = inspect.getsource(f)
                    func_source_hash = hash_method(
                        func_source_code.encode("utf-8"))
                    func_source_hash = str(func_source_hash.hexdigest())

                    cache_key += func_source_hash

                return cache_key

            decorated_function.uncached = f
            decorated_function.cache_timeout = timeout
            decorated_function.make_cache_key = default_make_cache_key

            return decorated_function

        return decorator

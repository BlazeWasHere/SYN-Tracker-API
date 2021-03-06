#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)

Call this file if `POPULATE_CACHE` has been set in `.env` and the site is up.
This script just triggers the functions to cache, ideally in the future
we set up a cron job or alike for this.
"""

from typing import List

import requests
import gevent

from syn.cron import routes

HOST = 'http://localhost:1337'

if __name__ == '__main__':
    jobs: List[gevent.Greenlet] = []

    for route in routes:
        jobs.append(gevent.spawn(requests.get, HOST + route))

    print(f'Waiting for {len(jobs)} jobs, this could take a few minutes.')
    gevent.joinall(jobs)

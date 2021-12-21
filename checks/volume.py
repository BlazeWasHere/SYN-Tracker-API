#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from gevent import monkey
import gevent

monkey.patch_all()

from utils.checker import check_bridge_volume, check_bridge_events

if __name__ == '__main__':
    chains = ["bsc"]

    jobs = []

    def dispatch(chain: str):
        return [
            check_bridge_volume(chain, token_name='nusd', skip_last_day=True),
            check_bridge_events(chain, skip_last_day=False)
        ]

    for chain in chains:
        jobs.append(gevent.spawn(dispatch, chain))

    gevent.joinall(jobs)

    for x in jobs:
        for z in x.get():
            print(z)

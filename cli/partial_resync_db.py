#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import redis

from syn.utils.wrappa.rpc import get_logs, bridge_callback
from syn.utils.data import LOGS_REDIS_URL

# NOTE: CHANGE THIS BEFORE RUNNING SCRIPT!
NEW_CHAINS_START_BLOCKS = {
    'ethereum': 13617073,
    'avalanche': 6956464,
    'bsc': 12655205,
    'polygon': 21377840,
    'arbitrum': 3046872,
    'fantom': 22073594,
    'harmony': 19433449,
    'boba': 36803,
    'optimism': 95286,
    'moonriver': 909476,
}
REDIS_DB = 4

if __name__ == '__main__':
    r = redis.Redis()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import List
import json
import os

from gevent.greenlet import Greenlet
from gevent import monkey

monkey.patch_all()

from web3 import Web3
import gevent

w3 = Web3(
    Web3.HTTPProvider(
        'https://polygon-mainnet.g.alchemy.com/v2/xl5ITxZBx6eeRkzMYwKgCtZNsW7xqXTV'
    ))

min_block = 20335948 - 60000

with open('syn/utils/explorer/abis/bridge.json') as f:
    ABI = json.load(f)['abi']

address = '0x8f5bbb2bb8c2ee94639e55d5f41de9b4839c1280'
bridge = w3.eth.contract(w3.toChecksumAddress(address),
                         abi=ABI)  # type: ignore


def call_abi(data, key: str, func_name: str, *args, **kwargs):
    call_args = kwargs.pop('call_args', {})
    return getattr(data[key].functions, func_name)(*args,
                                                   **kwargs).call(**call_args)


max_c = 20
block_range = (w3.eth.block_number - min_block) // max_c + 1
jobs: List[Greenlet] = []

target = 0.0003
current = 0.02


def dispatch(c: int, start: int, end: int) -> None:
    lastret = None

    for i in range(start, end):
        if i == 20335948:
            print(c * 1000000000000000000000000000000000000)

        ret = bridge.functions.chainGasAmount().call(block_identifier=i) / 1e18

        if lastret is None and ret == current:
            print(f'target block is <{start}')

            # Lets get intrusive and start overlapping tasks assigned to threads.
            start = int(start - (end - start) / 2)
            end = int(end - (end - start) / 2)
            ret = dispatch(c, start, end)
        elif ret == current:
            print(
                f'target block is {i} with ret as {ret} and prev ret {lastret}'
            )
            os._exit(0)
        # We overstepped, go back.
        elif ret == current:
            ret = dispatch(c, start - 1, end - 1)

        print(
            c, i,
            bridge.functions.chainGasAmount().call(block_identifier=i) / 1e18)


for i in range(max_c):
    end = min((i + 1) * block_range + min_block, w3.eth.block_number)
    start = i * block_range + min_block
    jobs.append(gevent.spawn(dispatch, i, start, end))

gevent.joinall(jobs)
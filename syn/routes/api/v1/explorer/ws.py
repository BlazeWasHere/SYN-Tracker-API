#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from collections import defaultdict
from datetime import datetime

from flask import current_app as app
from flask_socketio import SocketIO

from syn.utils.explorer.poll import AttributeDict, Direction, start as _start
from syn.utils.explorer.data import CHAINS, TOKENS_IN_POOL
from syn.utils.data import TOKEN_DECIMALS

socketio: SocketIO = app.socketio  # type: ignore

pending_addresses = defaultdict(dict)


def _convert_amount(chain: str, token: str, amount: int) -> float:
    return amount / 10**TOKEN_DECIMALS[chain][token.lower()]


def _callback(event: AttributeDict, chain: str, data: AttributeDict,
              method: str, direction: Direction) -> None:
    _chain = 'ethereum' if chain == 'eth' else chain

    if direction == Direction.OUT:
        from_token = TOKENS_IN_POOL[_chain][data['tokenIndexFrom']]
        _time = datetime.now().timestamp()

        json = {
            'address': data['to'],
            'to_chain': CHAINS[data['chainId']],
            'from_chain': chain,
            'amount': _convert_amount(chain, from_token, data['amount']),
            'time': _time,
            'txhash': event['transactionHash'].hex(),
            'from_token': from_token,
        }

        pending_addresses[data['to']] = {
            'chain': chain,
            'time': _time,
        }

        socketio.emit('bridge', json, broadcast=True)
    elif direction == Direction.IN:
        if data['to'] in pending_addresses:
            _data = pending_addresses[data['to']]
            to_token = TOKENS_IN_POOL[_chain][data['tokenIndexTo']]

            json = {
                'address': data['to'],
                'time_taken': datetime.now().timestamp() - _data['time'],
                'from_chain': _data['chain'],
                'to_chain': chain,
                'fee': data['fee'] / 10**18,  # Fee is in nUSD/nETH
                'to_token': to_token,
                'amount': _convert_amount(chain, to_token, data['amount']),
            }

            if method != 'mint':
                json.update({'success': data['swapSuccess']})

            socketio.emit('confirm', json, broadcast=True)
            del pending_addresses[data['to']]


def start() -> None:
    socketio.start_background_task(_start, _callback)

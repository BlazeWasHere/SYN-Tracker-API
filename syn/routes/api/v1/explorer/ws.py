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


def _callback(event: AttributeDict, _chain: str, data: AttributeDict,
              method: str, direction: Direction, logs: AttributeDict) -> None:
    chain = 'eth' if _chain == 'ethereum' else _chain

    if direction == Direction.OUT:
        to_chain = CHAINS[data['chainId']]

        try:
            if method not in ['TokenRedeem', 'TokenRedeemAndRemove']:
                from_token = logs[0].address
                to_token = TOKENS_IN_POOL[to_chain][data['tokenIndexTo']]
            elif method == 'TokenRedeem':
                to_token = from_token = data['token']
            else:
                from_token = data['token']
                to_token = TOKENS_IN_POOL[to_chain][data['swapTokenIndex']]

            _time = datetime.now().timestamp()

            json = {
                'address': data['to'],
                'to_chain': CHAINS[data['chainId']],
                'from_chain': chain,
                'amount': _convert_amount(chain, from_token, data['amount']),
                'time': _time,
                'txhash': event['transactionHash'].hex(),
                'from_token': from_token,
                'to_token': to_token,
            }

            pending_addresses[data['to']] = {
                'chain': chain,
                'time': _time,
                'from_token': from_token,
            }

            socketio.emit('bridge', json, broadcast=True)

        except:
            print(chain, event, data, method)
            raise
    elif direction == Direction.IN:
        if data['to'] in pending_addresses:
            try:
                _data = pending_addresses[data['to']]

                if method not in ['TokenWithdraw', 'TokenMint']:
                    to_token = TOKENS_IN_POOL[_chain][data['tokenIndexTo']]
                else:
                    to_token = data['token']

                json = {
                    'address': data['to'],
                    'time_taken': datetime.now().timestamp() - _data['time'],
                    'from_chain': _data['chain'],
                    'to_chain': chain,
                    'fee': data['fee'] / 10**18,  # Fee is in nUSD/nETH
                    'to_token': to_token,
                    'from_token': _data['from_token'],
                    'amount': _convert_amount(chain, to_token, data['amount']),
                    'txhash': event['transactionHash'].hex(),
                }

                if method not in ['mint', 'TokenMint']:
                    json.update({'success': data['swapSuccess']})

                socketio.emit('confirm', json, broadcast=True)
                del pending_addresses[data['to']]

            except:
                print(chain, event, data, method)
                raise


def start() -> None:
    socketio.start_background_task(_start, _callback)

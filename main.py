#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from functools import lru_cache, wraps
from typing import List
import time
import re

from flask import Flask, jsonify, send_from_directory
from gevent.greenlet import Greenlet
from gevent.pool import Pool
import cloudscraper
import requests
import gevent

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/synapse-2?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false"
NRV_URL = "https://bscscan.com/token/0x42f6f551ae042cbe50c739158b4f0cac0edb9096"
URLS = {
    "ethereum":
    "https://etherscan.io/token/0x0f2d719407fdbeff09d87557abb7232601fd9f29",
    "bsc":
    "https://bscscan.com/token/0xa4080f1778e69467e905b8d6f72f6e441f9e9484",
    "polygon":
    "https://polygonscan.com/token/0xf8f9efc0db77d8881500bb06ff5d6abc3070e695",
    "avalanche":
    "https://avascan.info/blockchain/c/token/0x1f1E7c893855525b303f99bDF5c3c05Be09ca251",
    "arbitrum":
    "https://arbiscan.io/token/0x080f6aed32fc474dd5717105dba5ea57268f46eb",
    "fantom":
    "https://ftmscan.com/token/0xE55e19Fb4F2D85af758950957714292DAC1e25B2",
}
# Data for the adaper: https://github.com/DefiLlama/DefiLlama-Adapters/blob/main/projects/synapse/index.js
DEFILLAMA_DATA = {
    "bridges": {
        "bsc": {
            "metaswap": "0x930d001b7efb225613ac7f35911c52ac9e111fa9",
            "usd-lp": "0xf0b8b631145d393a767b4387d08aa09969b2dfed",
            "obscure": "0x14016e85a25aeb13065688cafb43044c2ef86784",
            "obscure-decimals": 18
        },
        "ethereum": {
            "metaswap": "0x2796317b0fF8538F253012862c06787Adfb8cEb6",
            "obscure": "0x8e870d67f660d95d5be530380d0ec0bd388289e1",
            "obscure-decimals": 18
        },
        "polygon": {
            "metaswap": "0x96cf323E477Ec1E17A4197Bdcc6f72Bb2502756a",
            "usd-lp": "0x128a587555d1148766ef4327172129b50ec66e5d",
            "obscure": "0x104592a158490a9228070e0a8e5343b499e125d0",
            "obscure-decimals": 18
        },
        "avax": {
            "metaswap": "0xf44938b0125a6662f9536281ad2cd6c499f22004",
            "usd-lp": "0x55904f416586b5140a0f666cf5acf320adf64846",
            "obscure": "0x4fbf0429599460D327BD5F55625E30E4fC066095",
            "obscure-decimals": 18
        },
        "fantom": {
            "metaswap": "0xaed5b25be1c3163c907a471082640450f928ddfe",
            "obscure": "0x04068da6c83afcfa0e13ba15a6696662335d5b75",
            "obscure-decimals": 6
        },
        "arbitrum": {
            "obscure": "0x82af49447d8a07e3bd95bd0d56f35241523fbab1",
            "obscure-decimals": 18
        }
    },
    "subgraphs": {
        "bsc":
        "https://api.thegraph.com/subgraphs/name/aureliusbtc/bsc-synapse-amm",
        "ethereum":
        "https://api.thegraph.com/subgraphs/name/aureliusbtc/mainnet-synapse-amm",
        "polygon":
        "https://api.thegraph.com/subgraphs/name/aureliusbtc/polygon-synapse-amm",
        "avax":
        "https://api.thegraph.com/subgraphs/name/aureliusbtc/avalanche-synapse-amm",
        "arbitrum":
        "https://api.thegraph.com/subgraphs/name/aureliusbtc/arbitrum-synapse-amm",
        "fantom":
        "https://api.thegraph.com/subgraphs/name/aureliusbtc/fantom-synapse-amm"
    },
    "unsupported": ["nUSD", "Frapped USDT", "Magic Internet Money", "nETH"]
}

AVASCAN_RE = re.compile(r"<span class=\"amount\">(.*)<span>(.{3})<\/span>")
TOTAL_SUPPLY_RE = re.compile(r"total supply (.*), number")
# Some sites like etherscan use CF and love to ruin us!
s = cloudscraper.create_scraper()
app = Flask(__name__)
pool = Pool()


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


@timed_cache(60)
def get_chain_circ_cupply(chain: str) -> float:
    assert (chain in URLS)

    r = s.get(URLS[chain])

    if chain != 'avalanche':
        res = re.findall(TOTAL_SUPPLY_RE, r.text)
    else:
        res = re.findall(AVASCAN_RE, r.text)
        res[0] = res[0][0] + res[0][1]

    # Regex found.
    if len(res) > 0:
        # Convert 123,456,789.12 -> 123456789.12 (float)
        return float(res[0].replace(',', ''))
    else:
        print(
            f'Failed to find total supply from {chain!r} on response text {r.text}'
        )
        return -1


@timed_cache(60)
def get_current_price(currency: str = "usd") -> float:
    r = requests.get(COINGECKO_URL)
    return r.json()['market_data']['current_price'][currency]


# Some length of timed cache.
@timed_cache(60 * 30)
def get_all_chains_circ_supply() -> float:
    jobs: List[Greenlet] = []
    total: float = 0

    for chain in URLS:
        jobs.append(pool.spawn(get_chain_circ_cupply, chain))

    ret: List[Greenlet] = gevent.joinall(jobs)
    for x in ret:
        total += x.get()

    return round(total, 2)


@app.route('/')
def index():
    return send_from_directory('public', 'index.html')


@app.route('/defillama.json')
def defillama():
    return jsonify(DEFILLAMA_DATA)


@app.route('/mcap', methods=['GET'])
def mcap():
    return jsonify({
        'market_cap':
        round(get_current_price() * get_all_chains_circ_supply(), 2)
    })


@app.route('/circ', methods=['GET'])
def circ():
    return jsonify({'supply': get_all_chains_circ_supply()})


@app.route('/circ/<chain>', methods=['GET'])
def circ_chain(chain: str):
    if chain not in URLS:
        return (jsonify({
            'error': 'invalid chain',
            'valids': list(URLS.keys()),
        }), 400)

    ret = get_chain_circ_cupply(chain)
    if ret == -1:
        return (jsonify({'error':
                         'failed to get chain circulatory supply'}), 500)

    return jsonify({'success': True, 'supply': round(ret, 2)})


if __name__ == '__main__':
    app.run('0.0.0.0', port=1337)

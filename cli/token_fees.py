#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any, Dict, List, Union
from decimal import Decimal
import sys

from tabulate import tabulate
import requests


def analyze(data: Dict[str, Decimal],
            name: str) -> List[Union[str, Decimal, int, float]]:
    _data = list(data.values())
    _max = round(max(*_data), 2)
    _min = round(min(*_data), 2)
    _sum = round(sum(_data), 2)
    avg = round(_sum / len(_data), 2)

    ret = [name, _max, _min, _sum, avg]

    if '(USD)' in name:
        _ret = []
        for x in ret:
            if type(x) != str:
                x = f'${x:,}'

            _ret.append(x)

        return _ret

    return ret


if __name__ == '__main__':
    ENDPOINT = 'https://synapse.dorime.org/api/v1/analytics/fees/bridge/{chain}/{token}'

    _, chain, token = sys.argv

    r = requests.get(ENDPOINT.format(chain=chain, token=token))
    if not r.ok:
        print(f'error with args `{chain}` & `{token}`')
        print(r.text)
        exit(1)

    r = r.json(use_decimal=True)['data']

    tx_counts: Dict[str, Decimal] = {}
    usds: Dict[str, Decimal] = {}
    fees: Dict[str, Decimal] = {}
    data: List[Any] = []

    # Some aggregation.
    for k, v in r.items():
        data.append([k, v['fees'], v['price_usd'], v['tx_count']])
        # We can safely assume `k` is unique.
        tx_counts.update({k: v['tx_count']})
        usds.update({k: v['price_usd']})
        fees.update({k: v['fees']})

    stats: List[List[Any]] = []
    stats.append(analyze(tx_counts, 'Transactions'))
    stats.append(analyze(usds, 'Fees (USD)'))
    stats.append(analyze(fees, f'Fees ({token.upper()})'))

    args = {
        'tablefmt': 'presto',
        'disable_numparse': True,
        'numalign': 'right',
    }
    print(tabulate(data, headers=['date', 'fees', 'usd', 'tx_count'], **args))
    print(
        '\n',
        tabulate(stats,
                 headers=['Name', 'Max', 'Min', 'Total', 'Average'],
                 **args))

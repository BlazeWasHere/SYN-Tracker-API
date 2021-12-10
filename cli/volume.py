#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from collections import defaultdict
from decimal import Decimal
from typing import Dict
import random

from matplotlib import pyplot
import requests

URL = 'https://synapse.dorime.org/api/v1/analytics/volume/total/tx_count'

if __name__ == '__main__':
    r = requests.get(URL)
    if not r.ok:
        print(r.text, r.status_code)
        exit(1)

    chains_data: Dict[str, Dict[datetime, Decimal]] = defaultdict(dict)
    totals: Dict[datetime, Decimal] = {}
    r = r.json()['data']

    for chain, data in r.items():
        for date, val in data.items():
            if date != 'total':
                date = datetime.fromisoformat(date)

                if date > (datetime.today() - timedelta(days=1)):
                    continue

                assert date not in chains_data[chain]
                chains_data[chain][date] = val

    for chain, data in chains_data.items():
        for date, val in data.items():
            if date in totals:
                totals[date] += val
            else:
                totals.update({date: val})

    #pyplot.gca().yaxis.set_major_formatter('${x:1,.2f}')
    # NOTE: Uncomment below to add the `total` line.
    pyplot.plot(totals.keys(), totals.values(), label='total')

    # Plot per chain data now.
    #for chain, data in chains_data.items():
    #    pyplot.plot(
    #        data.keys(),
    #        data.values(),
    #        # Pick a random color.
    #        c=tuple(random.uniform(0, 1) for _ in range(3)),
    #        label=chain)

    pyplot.legend()
    pyplot.show()

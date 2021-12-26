#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example:
    python3 cli/nusd.py ethereum nusd 2021-10-01
    python3 cli/nusd.py arbitrum neth 2021-10-01

Note that most 4pools were created post 2021-11-07.
The API does not track the previous metapools.
"""

from datetime import datetime, timedelta
from typing import Dict, Generator
from decimal import Decimal
import sys

from matplotlib import pyplot
import requests


def date_range(start: datetime, till: datetime) -> Generator[str, None, None]:
    days = (till - start).days
    for i in range(days):
        yield str((start + timedelta(days=i)).date())


if __name__ == '__main__':
    DATE_ENDPOINT = 'https://synapse.dorime.org/api/v1/utils/date2block/{chain}/{date}'
    VP_ENDPOINT = 'https://synapse.dorime.org/api/v1/analytics/pools/price/virtual/{chain}'

    stats: Dict[datetime, Decimal] = {}
    _, chain, pool, from_date = sys.argv

    from_date = datetime.fromisoformat(from_date)
    till_date = datetime.now()

    for date in date_range(from_date, till_date):
        try:
            r = requests.get(DATE_ENDPOINT.format(chain=chain, date=date))
            r.raise_for_status()

            block = r.json()[date]['block']
            r = requests.get(VP_ENDPOINT.format(chain=chain),
                             params={'block': block})
            r.raise_for_status()

            date = datetime.fromisoformat(date)
            stats[date] = r.json(use_decimal=True)[pool]
        except Exception:
            continue

    pyplot.subplots()[1].ticklabel_format(useOffset=False)
    pyplot.plot(stats.keys(),
                stats.values(),
                label=f'Virtual Price for {pool} on {chain}')

    pyplot.legend()
    pyplot.show()

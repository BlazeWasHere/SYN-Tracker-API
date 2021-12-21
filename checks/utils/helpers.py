#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dateutil import parser
from datetime import datetime, timedelta, date
import decimal
import time
from typing import Callable, Any, Dict, Optional, Union, List

import requests
import simplejson as simplejson
from requests import Response

from data import AIRDROP, ALIAS

LAST_TEXT = ''
LAST_LEN = 0

MAX_TIMEOUT = 5


def add_dicts(dict_total: Dict[str, int], dict_to_add: Dict[str, int]) -> None:
    for k, v in dict_to_add.items():
        dict_total[k] += v


def add_to_dict(dict_total: Dict[str, Dict[str, int]],
                dict_to_add: Dict[str, int], key: str) -> None:
    if key not in dict_total:
        dict_total[key] = dict()
        for _k in dict_to_add:
            dict_total[key][_k] = 0

    add_dicts(dict_total[key], dict_to_add)


def extract_address_volume(volume: Dict[str, Any],
                           token: str) -> Optional[str]:
    for data in volume.values():
        address = find_token_address(data['stats']['volume'], token)
        if address:
            return address

    return None


def find_token_address(data: Dict[str, Any], token: str) -> Optional[str]:
    for address, address_stats in data.items():
        _t = address_stats['token']
        if _t == token or (_t in ALIAS and ALIAS[_t] == token):
            return address

    return None


def get_json_timeout(func: Callable[[Any], Response], *args: Any,
                     **kwargs: Any) -> Dict[str, Any]:
    """
        Cals func(*args, **kwargs) until
        there's no timeout with incremental sleeping time
    """
    is_done = False
    if 'timeout' not in kwargs:
        kwargs['timeout'] = 5
    sleep_time = 1
    result = None
    while not is_done:
        try:
            # result = func(*args, **kwargs).json()
            result = func(*args, **kwargs).json(use_decimal=True)
            is_done = True
        except (requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError,
                simplejson.JSONDecodeError) as e:
            print(e)
            print_over(f' [sleeping for {sleep_time}s]', to_add=True)
            time.sleep(sleep_time)
            if sleep_time < MAX_TIMEOUT:
                sleep_time += 1

    return result


def get_last_x_dates(num_days: int) -> List[str]:
    base = datetime.today().date() - \
           timedelta(days=num_days - 1)

    return [f'{base + timedelta(days=x)}' for x in range(num_days)]


def get_dates_between(date_from: str, date_to: str) -> List[str]:
    d = parser.parse(date_from)
    d_to = parser.parse(date_to)
    result = [date_from]
    while d != d_to:
        d += timedelta(days=1)
        result.append(f'{d.date()}')

    return result


def print_over(text='', to_add=False):
    """
        Prints text without newline and returns to the first symbol
    """
    global LAST_TEXT, LAST_LEN

    if to_add:
        text = LAST_TEXT + text
    elif LAST_LEN > 0:
        print(' ' * LAST_LEN, end='\r')

    print(text, end="\r")

    LAST_LEN = len(text)

    if not to_add:
        LAST_TEXT = text


def cut_float(f: Union[float, decimal.Decimal], precision=1) -> str:
    threshold = 10**precision

    tmp = f
    decimals = 0
    while tmp < threshold:
        tmp *= 10
        decimals += 1

    if decimals == 0:
        return f'{int(f)}'

    if int(tmp) % 10 == 0 and decimals > 1:
        decimals -= 1

    # full_len = len(f'{int(f)}') + 1 + decimals
    result = f'{f:.{decimals}f}'
    return result


def get_signed_int(num: Union[decimal.Decimal, float, int]) -> str:
    return f'{int(num):+,}'


def get_unsigned_int(num: Union[decimal.Decimal, float, int]) -> str:
    return f'{int(num):,}'


def hex_to_int(str_hex: str) -> int:
    """
    Convert 0xdead1234 into integer
    """
    return int(str_hex[2:], 16)


def get_date_from_ts(ts: Union[int, str]) -> str:
    d = datetime.utcfromtimestamp(int(ts)).date()
    return f'{d}'


def slice_by_month(date_from: str) -> List[List[str]]:
    today = f'{datetime.today().date()}'
    dates = get_dates_between(date_from, today)
    month = ''
    result = []
    last = []
    for _date in dates:
        _m = _date[:7]  # extract YYYY-mm
        if _m != month:
            if month != '':
                result.append(last)
                last = []
            month = _m
        last.append(_date)

    result.append(last)

    return result


def get_month_dates(month: str) -> List[str]:
    date_from = parser.parse(month + '-01').date()
    date_to = date_from + timedelta(days=31)
    date_to = date(year=date_to.year, month=date_to.month,
                   day=1) - timedelta(days=1)
    return get_dates_between(f'{date_from}', f'{date_to}')

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from datetime import datetime

from werkzeug.routing import BaseConverter, ValidationError
from flask import Flask
import dateutil.parser


class DatetimeConverter(BaseConverter):
    def to_python(self, value: str) -> datetime:
        try:
            return dateutil.parser.parse(value)
        except dateutil.parser.ParserError:
            raise ValidationError

    def to_url(self, value: datetime) -> str:
        return super().to_url(value)


def register_converter(app: Flask, name: str) -> None:
    func = None

    if name == 'date':
        func = DatetimeConverter

    if func is None:
        raise TypeError(f'{name} is invalid: no converter found.')

    app.url_map.converters[name] = func
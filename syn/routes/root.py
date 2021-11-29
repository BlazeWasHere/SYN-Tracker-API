#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

import json
import os

from flask import Blueprint, jsonify

# Get parent (root) dir.
_path = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
openapi_folder = os.path.join(_path, 'docs', 'openapi')
template_folder = os.path.join(_path, 'public')
root_bp = Blueprint('root_bp', __name__, static_folder=template_folder)

with open(os.path.join(openapi_folder, 'specification.json')) as f:
    OPENAPI_DATA = json.load(f)


@root_bp.route('/')
def index():
    return root_bp.send_static_file('index.html')


@root_bp.route('/openapi.json')
def openapi():
    return jsonify(OPENAPI_DATA)

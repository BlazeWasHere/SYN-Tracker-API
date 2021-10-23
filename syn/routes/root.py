#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import List, Optional
import os

from flask import Blueprint, render_template, current_app as app, jsonify

from syn.utils.data import DEFILLAMA_DATA, SYN_DATA

# Get parent (root) dir.
_path = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
template_folder = os.path.join(_path, 'public')
root_bp = Blueprint('root_bp', __name__, template_folder=template_folder)


@root_bp.route('/')
def index():
    routes: List[Optional[str]] = []

    for x in app.url_map.iter_rules():
        x = str(x)

        if x.startswith('/api'):
            if '<chain>' in x:
                _route = x.split('<chain>')[0]

                for chain in SYN_DATA:
                    routes.append(_route + chain)

                routes.append(None)
            else:
                routes.append(x)
                routes.append(None)

    return render_template('index.html', routes=routes)


@root_bp.route('/defillama.json')
def defillama():
    return jsonify(DEFILLAMA_DATA)
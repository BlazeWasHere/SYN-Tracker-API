#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Any, List, Dict, Union

from gevent.greenlet import Greenlet
from gevent.pool import Pool
import requests
import gevent

from syn.utils.cache import timed_cache

pool = Pool()

CHAIN_MAPPING = {
    'eth': 1,
    'polygon': 137,
    'bsc': 56,
    'avalanche': 43114,
    'fantom': 250
}


class Covalent(object):
    """
	Simple covalenthq.com wrapper
	https://www.covalenthq.com/docs/api
	"""
    def __init__(self,
                 api_key: str,
                 url: str = 'https://api.covalenthq.com/v1/') -> None:
        self.session = requests.Session()
        self.api_key = api_key
        self.base = url

    def __request(self, method: str, endpoint: str, *args, **kwargs) -> Any:
        params = kwargs.pop('params', {})
        params.update({'key': self.api_key})

        chain = CHAIN_MAPPING[kwargs.pop('chain', 'eth')]

        r = self.session.request(method,
                                 f'{self.base}{chain}{endpoint}',
                                 *args,
                                 **kwargs,
                                 params=params)

        try:
            return r.json()
        except Exception as e:
            # Some debug info incase there is an error.
            print(r.text)
            raise e

    def _paginate(self, *args, **kwargs) -> List[Any]:
        jobs: List[Greenlet] = []
        res: List[Any] = []

        offset = kwargs.pop('offset', 0)
        ret = self.__request(*args,
                             **kwargs,
                             params={
                                 'skip': offset,
                                 'page-size': 750
                             })

        offset += int(ret['data']['pagination']['page_size'])
        res += [ret['data']]

        needed = ret['data']['pagination']['total_count'] // offset + 1

        # Workers, dispatch!
        for i in range(1, needed):
            jobs.append(
                pool.spawn(self.__request,
                           *args,
                           **kwargs,
                           params={
                               'skip': offset * i,
                               'page-size': 750
                           }))

        _ret: List[Greenlet] = gevent.joinall(jobs)
        for x in _ret:
            res += [x.get()['data']]  # type: ignore

        return res

    @timed_cache(60, maxsize=25)
    def transfers_v2(self, address: str, contract_address: str,
                     chain: str) -> List[Dict[str, Any]]:
        """
		Get ERC20 token transfers. Passing in an ENS resolves automatically.

		Args:
			address (str): the evm compatible address
			contract_address (str): the contract address to query

		Schema:
		{
			"address":"0x0000000000000000000000000000000000000000",
			"updated_at":"2021-10-29T20:03:59.587833972Z",
			"next_update_at":"2021-10-29T20:08:59.587834232Z",
			"quote_currency":"USD",
			"chain_id":56,
			"items":[
				{
					"block_signed_at":"2021-10-29T16:27:09Z",
					"block_height":12196722,
					"tx_hash":"0xa07b339a1293f28ff73cb80090e1354e85aefbffd3f33eacb86ad37e212b6381",
					"tx_offset":376,
					"successful":true,
					"from_address":"0xb612adad667074d4a8f35f6697d607c9482e46c1",
					"from_address_label":null,
					"to_address":"0x8027a7fa5753c8873e130f1205da9fb8691726ab",
					"to_address_label":null,
					"value":"0",
					"value_quote":null,
					"gas_offered":106643,
					"gas_spent":80782,
					"gas_price":5000000000,
					"gas_quote":0.21206909474670413,
					"gas_quote_rate":525.0404663085938,
					"transfers":[
					{
						"block_signed_at":"2021-10-29T16:27:09Z",
						"tx_hash":"0xa07b339a1293f28ff73cb80090e1354e85aefbffd3f33eacb86ad37e212b6381",
						"from_address":"0x8027a7fa5753c8873e130f1205da9fb8691726ab",
						"from_address_label":null,
						"to_address":"0x0000000000000000000000000000000000000000",
						"to_address_label":null,
						"contract_decimals":18,
						"contract_name":"Synapse",
						"contract_ticker_symbol":"SYN",
						"contract_address":"0xa4080f1778e69467e905b8d6f72f6e441f9e9484",
						"logo_url":"",
						"transfer_type":"IN",
						"delta":"3000000000000000000",
						"balance":null,
						"quote_rate":3.2531380653381348,
						"delta_quote":9.759414196014404,
						"balance_quote":null,
						"method_calls":null
					}
					]
				}
			}
		"""
        return self._paginate(
            'GET',
            f'/address/{address}/transfers_v2/?contract-address={contract_address}',
            chain=chain)

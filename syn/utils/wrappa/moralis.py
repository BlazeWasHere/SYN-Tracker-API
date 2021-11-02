#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
		  Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
	(See accompanying file LICENSE_1_0.txt or copy at
		  https://www.boost.org/LICENSE_1_0.txt)
"""

from typing import Any, Dict, List, Optional

from gevent.greenlet import Greenlet
from gevent.pool import Pool
import requests
import gevent

from syn.utils.data import POPULATE_CACHE
from syn.utils.cache import timed_cache
from syn.utils.helpers import raise_if

if POPULATE_CACHE:
    import time

pool = Pool()


class Moralis(object):
    """
	Simple moralis.io wrapper
	https://deep-index.moralis.io/api-docs
	"""
    def __init__(self,
                 api_key: str,
                 url: str = 'https://deep-index.moralis.io/api/v2') -> None:
        self.base = url
        self.session = requests.Session()
        self.session.headers['x-api-key'] = api_key

    def __request(self, method: str, endpoint: str, *args, **kwargs) -> Any:
        r = self.session.request(method, self.base + endpoint, *args, **kwargs)

        try:
            return r.json()
        except Exception as e:
            # Some debug info incase there is an error.
            print(r.text)
            raise e

    def _paginate(self, *args, **kwargs) -> List[Any]:
        jobs: List[Greenlet] = []
        res: List[Any] = []

        useRedisCache = kwargs.pop('useRedis', False)
        offset = kwargs.pop('offset', 0)

        if useRedisCache:
            # Equivalent of 1 request.
            needed = 2
        else:
            ret = self.__request(*args, **kwargs, params={'offset': offset})

            offset += int(ret['page_size'])
            res += ret['result']

            needed = ret['total'] // offset + 1

        # Workers, dispatch!
        for i in range(1, needed):
            jobs.append(
                pool.spawn(self.__request,
                           *args,
                           **kwargs,
                           params={'offset': offset * i}))

            if POPULATE_CACHE:
                # 3600 r/m limit, so about 0.0167 r/s.
                time.sleep(0.015)

        _ret: List[Greenlet] = gevent.joinall(jobs)
        for x in _ret:
            res += raise_if(x.get(), None)['result']

        return res

    def transactions(self,
                     address: str,
                     chain: str = 'eth',
                     offset: int = 0) -> List[Dict[str, Optional[str]]]:
        """
		Gets native transactions in descending order.

		Args:
			address (str): the evm compatible address
			chain (str, optional): the evm chain. Defaults to 'eth'.
			offset (int, optional): start from this point. Defaults to 0.

		Schema:
		{
			"hash": "0x4586c49359d6a3da84115cf18702e9f7b306a73bc27a3369d99de881a2dabb9f",
			"nonce": "7229",
			"transaction_index": "330",
			"from_address": "0x230a1ac45690b9ae1176389434610b9526d2f21b",
			"to_address": "0x2796317b0ff8538f253012862c06787adfb8ceb6",
			"value": "0",
			"gas": "1000000",
			"gas_price": "100791369929",
			"input": "0x1cf5f07f000000000000000000000000dd011bc8d5f5b9c716e711b515a044346e4104c6000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc200000000000000000000000000000000000000000000000000d44db4ac6062ef0000000000000000000000000000000000000000000000000011c37937e08000f4bf5a81a13434e31af211ca9410afb109e635bfb0e744091162b93bfde14a1d",
			"receipt_cumulative_gas_used": "19825446",
			"receipt_gas_used": "96698",
			"receipt_contract_address": null,
			"receipt_root": null,
			"receipt_status": "1",
			"block_timestamp": "2021-10-26T13:10:09.000Z",
			"block_number": "13493199",
			"block_hash": "0xf052fad32e3d61298f476d5c5ca577bc99f3bb56693dabcb5b20a442b26cd950"
		}
		"""

        return self._paginate('GET',
                              f'/{address}?chain={chain}',
                              offset=offset)

    @timed_cache(60, maxsize=25)
    def erc20_transfers(self,
                        address: str,
                        chain: str = 'eth',
                        offset: int = 0,
                        **kwargs) -> List[Dict[str, str]]:
        """
		Gets ERC20 token transactions in descending order.

		Args:
			address (str): the evm compatible address
			chain (str, optional): the evm chain. Defaults to 'eth'.
			offset (int, optional): start from this point. Defaults to 0.

		Schema:
		{
			"transaction_hash": "0x98ff3bbf7fac00576f8c741c18989b68eee6ea2e5d3e6b951b19e6d2e8557a66",
			"address": "0x1b84765de8b7566e4ceaf4d0fd3c5af52d3dde4f",
			"block_timestamp": "2021-10-26T13:32:19.000Z",
			"block_number": "13493284",
			"block_hash": "0x8015a566188783738327b549f5df7a4d77f458d82653f4f985aeb6876d896ca8",
			"to_address": "0x2796317b0ff8538f253012862c06787adfb8ceb6",
			"from_address": "0xa2569370a9d4841c9a62fc51269110f2eb7e0171",
			"value": "34422533639057896327970"
		}
		"""
        return self._paginate('GET',
                              f'/{address}/erc20/transfers?chain={chain}',
                              offset=offset,
                              **kwargs)

    @timed_cache(60, maxsize=25)
    def erc20_balances(self,
                       address: str,
                       chain: str = 'eth',
                       to_block: int = 0) -> List[Dict[str, Any]]:
        """
		Gets token balances for a specific address.

		Args:
			address (str): the evm compatible address
			chain (str, optional): the evm chain. Defaults to 'eth'.
			to_block (Optional[int], optional): the block height. Defaults to None.

		Returns:
			List[Dict[str, Optional[str]]]: list of token balances

		Schema:
		{
			"token_address": "0x0f2d719407fdbeff09d87557abb7232601fd9f29",
			"name": "Synapse",
			"symbol": "SYN",
			"logo": null,
			"thumbnail": null,
			"decimals": "18",
			"balance": "87719066447989719155743"
		}
		"""
        return self.__request('GET',
                              f'/{address}/erc20?chain={chain}',
                              params={'to_block': to_block})

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
          Copyright Blaze 2021.
 Distributed under the Boost Software License, Version 1.0.
    (See accompanying file LICENSE_1_0.txt or copy at
          https://www.boost.org/LICENSE_1_0.txt)
"""

from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
import logging

import dateutil.parser

from syn.utils.data import REDIS, POPULATE_CACHE, MESSAGE_QUEUE_REDIS
from syn.utils.cache import redis_cache, _serialize_args_to_str
from syn.utils.helpers import date_range

logger = logging.Logger(__name__)


class CoingeckoIDS(Enum):
    HIGH = 'highstreet'
    SYN = 'synapse-2'
    USDT = 'tether'
    USDC = 'usd-coin'
    BUSD = 'binance-usd'
    DAI = 'dai'
    ETH = 'ethereum'
    DOG = 'the-doge-nft'
    NRV = 'nerve-finance'
    MIM = 'magic-internet-money'
    FRAX = 'frax'
    BNB = 'binancecoin'
    AVAX = 'avalanche-2'
    ONE = 'harmony'
    MATIC = 'matic-network'
    FTM = 'fantom'
    MOVR = 'moonriver'
    NFD = 'feisty-doge-nft'
    JUMP = 'hyperjump'
    OHM = 'olympus'
    WSOHM = 'wrapped-staked-olympus'
    JGN = 'juggernaut'
    GOHM = 'governance-ohm'
    SOLAR = 'solarbeam'
    GMX = 'gmx'
    GLMR = 'moonbeam'
    CRO = 'crypto-com-chain'
    METIS = 'metis-token'
    NEWO = 'new-order'
    SDT = 'stake-dao'
    LUNA = 'terra-luna'
    JEWEL = 'defi-kingdoms'
    XJEWEL = 'xjewel'
    UST = 'terrausd'


CUSTOM = {
    'ethereum': {
        # nUSD
        '0x1b84765de8b7566e4ceaf4d0fd3c5af52d3dde4f': 1,
        # USDB
        '0x02b5453d92b730f29a86a0d5ef6e930c4cf8860b': 1,
    },
    'bsc': {
        # nUSD
        '0x23b891e5c62e0955ae2bd185990103928ab817b3': 1,
        # USD-LP
        '0xf0b8b631145d393a767b4387d08aa09969b2dfed': 1,
        # BSC-USD
        '0x55d398326f99059ff775485246999027b3197955': 1,
        '0xdfd717f4e942931c98053d5453f803a1b52838db': 0,
        # JUMP, not really it's price but oh well.
        '0x130025ee738a66e691e6a7a62381cb33c6d9ae83': 0.01,
        # USDB
        '0xc8699abbba90c7479dedccef19ef78969a2fc608': 1,
    },
    'polygon': {
        # nUSD
        '0xb6c473756050de474286bed418b77aeac39b02af': 1,
        '0x81067076dcb7d3168ccf7036117b9d72051205e2': 0,
        # USD-LP
        '0x128a587555d1148766ef4327172129b50ec66e5d': 1,
        # USDB
        '0xfa1fbb8ef55a4855e5688c0ee13ac3f202486286': 1,
    },
    'avalanche': {
        # nUSD
        '0xcfc37a6ab183dd4aed08c204d1c2773c0b1bdf46': 1,
        # USD-LP
        '0x55904f416586b5140a0f666cf5acf320adf64846': 1,
        # USDB
        '0x5ab7084cb9d270c2cb052dd30dbecbca42f8620c': 1,
    },
    'arbitrum': {
        # nUSD
        '0x2913e812cf0dcca30fb28e6cac3d2dcff4497688': 1,
        # USD-LP
        '0xe264cb5a941f98a391b9d5244378edf79bf5c19e': 1,
    },
    'fantom': {
        # nUSD
        '0xed2a7edd7413021d440b09d654f3b87712abab66': 1,
        # JUMP, not really it's price but oh well.
        '0x78de9326792ce1d6eca0c978753c6953cdeedd73': 0.01,
        # USD-LP
        '0x43cf58380e69594fa2a5682de484ae00edd83e94': 1,
        # USDB
        '0x6fc9383486c163fa48becdec79d6058f984f62ca': 1,
    },
    'harmony': {
        # nUSD
        '0xed2a7edd7413021d440b09d654f3b87712abab66': 1,
    },
    'boba': {
        # nUSD
        '0x6b4712ae9797c199edd44f897ca09bc57628a1cf': 1,
    },
    'moonriver': {
        # USDB
        '0x3e193c39626bafb41ebe8bdd11ec7cca9b3ec0b2': 1,
    },
    'optimism': {},
    'aurora': {
        # nUSD
        '0x07379565cd8b0cae7c60dc78e7f601b34af2a21c': 1,
    },
    'moonbeam': {},
    'cronos': {
        # nUSD
        '0x396c9c192dd323995346632581bef92a31ac623b': 1,
    },
    'metis': {
        # nUSD
        '0x961318fc85475e125b99cc9215f62679ae5200ab': 1,
    },
    'dfk': {
        # nUSD
        '0x52285d426120ab91f378b3df4a15a036a62200ae': 1,
    },
}

ADDRESS_TO_CGID = {
    'ethereum': {
        '0x71ab77b7dbb4fa7e017bc15090b2163221420282': CoingeckoIDS.HIGH,
        '0x0f2d719407fdbeff09d87557abb7232601fd9f29': CoingeckoIDS.SYN,
        '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2': CoingeckoIDS.ETH,
        '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48': CoingeckoIDS.USDC,
        '0x6b175474e89094c44da98b954eedeac495271d0f': CoingeckoIDS.DAI,
        '0xdac17f958d2ee523a2206206994597c13d831ec7': CoingeckoIDS.USDT,
        '0xbaac2b4491727d78d2b78815144570b9f2fe8899': CoingeckoIDS.DOG,
        '0x853d955acef822db058eb8505911ed77f175b99e': CoingeckoIDS.FRAX,
        '0xca76543cf381ebbb277be79574059e32108e3e65': CoingeckoIDS.WSOHM,
        '0x0ab87046fbb341d058f17cbc4c1133f25a20a52f': CoingeckoIDS.GOHM,
        '0x98585dfc8d9e7d48f0b1ae47ce33332cf4237d96': CoingeckoIDS.NEWO,
        '0x73968b9a57c6e53d41345fd57a6e6ae27d6cdb2f': CoingeckoIDS.SDT,
        '0x0261018aa50e28133c1ae7a29ebdf9bd21b878cb': CoingeckoIDS.UST,
    },
    'bsc': {
        '0xe9e7cea3dedca5984780bafc599bd69add087d56': CoingeckoIDS.BUSD,
        '0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d': CoingeckoIDS.USDC,
        '0xaa88c603d142c371ea0eac8756123c5805edee03': CoingeckoIDS.DOG,
        '0xa4080f1778e69467e905b8d6f72f6e441f9e9484': CoingeckoIDS.SYN,
        '0x5f4bde007dc06b867f86ebfe4802e34a1ffeed63': CoingeckoIDS.HIGH,
        '0x55d398326f99059ff775485246999027b3197955': CoingeckoIDS.USDT,
        '0x0fe9778c005a5a6115cbe12b0568a2d50b765a51': CoingeckoIDS.NFD,
        '0x42f6f551ae042cbe50c739158b4f0cac0edb9096': CoingeckoIDS.NRV,
        '0xc13b7a43223bb9bf4b69bd68ab20ca1b79d81c75': CoingeckoIDS.JGN,
        '0x88918495892baf4536611e38e75d771dc6ec0863': CoingeckoIDS.GOHM,
        '0xb7a6c5f0cc98d24cf4b2011842e64316ff6d042c': CoingeckoIDS.UST,
    },
    'polygon': {
        '0xf8f9efc0db77d8881500bb06ff5d6abc3070e695': CoingeckoIDS.SYN,
        '0x8f3cf7ad23cd3cadbd9735aff958023239c6a063': CoingeckoIDS.DAI,
        '0x2791bca1f2de4661ed88a30c99a7a9449aa84174': CoingeckoIDS.USDC,
        '0xc2132d05d31c914a87c6611c10748aeb04b58e8f': CoingeckoIDS.USDT,
        '0x0a5926027d407222f8fe20f24cb16e103f617046': CoingeckoIDS.NFD,
        '0xd8ca34fd379d9ca3c6ee3b3905678320f5b45195': CoingeckoIDS.GOHM,
        '0xeee3371b89fc43ea970e908536fcddd975135d8a': CoingeckoIDS.DOG,
        '0x48a34796653afdaa1647986b33544c911578e767': CoingeckoIDS.FRAX,
        '0x7ceb23fd6bc0add59e62ac25578270cff1b9f619': CoingeckoIDS.ETH,
        '0x565098cba693b3325f9fe01d41b7a1cd792abab1': CoingeckoIDS.UST,
    },
    'avalanche': {
        '0x1f1e7c893855525b303f99bdf5c3c05be09ca251': CoingeckoIDS.SYN,
        '0xd586e7f844cea2f87f50152665bcbc2c279d8d70': CoingeckoIDS.DAI,
        '0xa7d7079b0fead91f3e65f86e8915cb59c1a4c664': CoingeckoIDS.USDC,
        '0xc7198437980c041c805a1edcba50c1ce5db95118': CoingeckoIDS.USDT,
        '0xf1293574ee43950e7a8c9f1005ff097a9a713959': CoingeckoIDS.NFD,
        '0x19e1ae0ee35c0404f835521146206595d37981ae': CoingeckoIDS.ETH,
        '0x321e7092a180bb43555132ec53aaa65a5bf84251': CoingeckoIDS.GOHM,
        '0xcc5672600b948df4b665d9979357bef3af56b300': CoingeckoIDS.FRAX,
        '0x53f7c5869a859f0aec3d334ee8b4cf01e3492f21': CoingeckoIDS.ETH,
        '0x62edc0692bd897d2295872a9ffcac5425011c661': CoingeckoIDS.GMX,
        '0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7': CoingeckoIDS.AVAX,
        '0x20a9dc684b4d0407ef8c9a302beaaa18ee15f656': CoingeckoIDS.GMX,
        '0x4bfc90322dd638f81f034517359bd447f8e0235a': CoingeckoIDS.NEWO,
        '0xccbf7c451f81752f7d2237f2c18c371e6e089e69': CoingeckoIDS.SDT,
        '0x997ddaa07d716995de90577c123db411584e5e46': CoingeckoIDS.JEWEL,
        '0xe97097de8d6a17be3c39d53ae63347706dcf8f43': CoingeckoIDS.UST,
    },
    'arbitrum': {
        '0x080f6aed32fc474dd5717105dba5ea57268f46eb': CoingeckoIDS.SYN,
        '0x3ea9b0ab55f34fb188824ee288ceaefc63cf908e': CoingeckoIDS.ETH,
        '0xff970a61a04b1ca14834a43f5de4533ebddb5cc8': CoingeckoIDS.USDC,
        '0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9': CoingeckoIDS.USDT,
        '0xfea7a6a0b346362bf88a9e4a88416b77a57d6c2a': CoingeckoIDS.MIM,
        '0x82af49447d8a07e3bd95bd0d56f35241523fbab1': CoingeckoIDS.ETH,
        '0x8d9ba570d6cb60c7e3e0f31343efe75ab8e65fb1': CoingeckoIDS.GOHM,
        '0x85662fd123280827e11c59973ac9fcbe838dc3b4': CoingeckoIDS.FRAX,
        '0xfc5a1a6eb076a2c7ad06ed22c90d7e710e35ad0a': CoingeckoIDS.GMX,
        '0x0877154a755b24d499b8e2bd7ecd54d3c92ba433': CoingeckoIDS.NEWO,
        '0x1a4da80967373fd929961e976b4b53ceec063a15': CoingeckoIDS.LUNA,
        '0x13780e6d5696dd91454f6d3bbc2616687fea43d0': CoingeckoIDS.UST,
    },
    'fantom': {
        '0xe55e19fb4f2d85af758950957714292dac1e25b2': CoingeckoIDS.SYN,
        '0x82f0b8b456c1a451378467398982d4834b6829c1': CoingeckoIDS.MIM,
        '0x04068da6c83afcfa0e13ba15a6696662335d5b75': CoingeckoIDS.USDC,
        '0x049d68029688eabf473097a2fc38ef61633a3c7a': CoingeckoIDS.USDT,
        '0x91fa20244fb509e8289ca630e5db3e9166233fdc': CoingeckoIDS.GOHM,
        '0x1852f70512298d56e9c8fdd905e02581e04ddb2a': CoingeckoIDS.FRAX,
        '0x67c10c397dd0ba417329543c1a40eb48aaa7cd00': CoingeckoIDS.ETH,
        '0x74b23882a30290451a17c44f4f05243b6b58c76d': CoingeckoIDS.ETH,
        '0xe3c82a836ec85311a433fbd9486efaf4b1afbf48': CoingeckoIDS.SDT,
        '0xa0554607e477cdc9d0ee2a6b087f4b2dc2815c22': CoingeckoIDS.UST,
    },
    'harmony': {
        '0xe55e19fb4f2d85af758950957714292dac1e25b2': CoingeckoIDS.SYN,
        '0xef977d2f931c1978db5f6747666fa1eacb0d0339': CoingeckoIDS.DAI,
        '0x985458e523db3d53125813ed68c274899e9dfab4': CoingeckoIDS.USDC,
        '0x3c2b8be99c50593081eaa2a724f0b8285f5aba8f': CoingeckoIDS.USDT,
        '0xcf664087a5bb0237a0bad6742852ec6c8d69a27a': CoingeckoIDS.ONE,
        '0x1852f70512298d56e9c8fdd905e02581e04ddb2a': CoingeckoIDS.FRAX,
        '0xfa7191d292d5633f702b0bd7e3e3bccc0e633200': CoingeckoIDS.FRAX,
        '0x67c10c397dd0ba417329543c1a40eb48aaa7cd00': CoingeckoIDS.GOHM,
        '0x0b5740c6b4a97f90ef2f0220651cca420b868ffb': CoingeckoIDS.ETH,
        '0xe3c82a836ec85311a433fbd9486efaf4b1afbf48': CoingeckoIDS.SDT,
        '0xd9eaa386ccd65f30b77ff175f6b52115fe454fd6': CoingeckoIDS.AVAX,
        '0x28b42698caf46b4b012cf38b6c75867e0762186d': CoingeckoIDS.JEWEL,
        '0xa0554607e477cdc9d0ee2a6b087f4b2dc2815c22': CoingeckoIDS.UST,
    },
    'boba': {
        '0xb554a55358ff0382fb21f0a478c3546d1106be8c': CoingeckoIDS.SYN,
        '0xf74195bb8a5cf652411867c5c2c5b8c2a402be35': CoingeckoIDS.DAI,
        '0x5de1677344d3cb0d7d465c10b72a8f60699c062d': CoingeckoIDS.USDT,
        '0x66a2a913e447d6b4bf33efbec43aaef87890fbbc': CoingeckoIDS.USDC,
        '0x96419929d7949d6a801a6909c145c8eef6a40431': CoingeckoIDS.ETH,
        '0xd203de32170130082896b4111edf825a4774c18e': CoingeckoIDS.ETH,
        '0xd22c0a4af486c7fa08e282e9eb5f30f9aaa62c95': CoingeckoIDS.GOHM,
        '0x61a269a9506272d128d79abfe8e8276570967f00': CoingeckoIDS.UST,
    },
    'moonriver': {
        '0xd80d8688b02b3fd3afb81cdb124f188bb5ad0445': CoingeckoIDS.SYN,
        '0xe96ac70907fff3efee79f502c985a7a21bce407d': CoingeckoIDS.FRAX,
        '0x3bf21ce864e58731b6f28d68d5928bcbeb0ad172': CoingeckoIDS.GOHM,
        '0x76906411d07815491a5e577022757ad941fb5066': CoingeckoIDS.SOLAR,
        '0x98878b06940ae243284ca214f92bb71a2b032b8a': CoingeckoIDS.MOVR,
        '0x1a93b23281cc1cde4c4741353f3064709a16197d': CoingeckoIDS.FRAX,
        '0xa9d0c0e124f53f4be1439ebc35a9c73c0e8275fb': CoingeckoIDS.UST,
    },
    'optimism': {
        '0x5a5fff6f753d7c11a56a52fe47a177a87e431655': CoingeckoIDS.SYN,
        '0x809dc529f07651bd43a172e8db6f4a7a0d771036': CoingeckoIDS.ETH,
        '0x121ab82b49b2bc4c7901ca46b8277962b4350204': CoingeckoIDS.ETH,
        '0x0b5740c6b4a97f90ef2f0220651cca420b868ffb': CoingeckoIDS.GOHM,
        '0x931b8f17764362a3325d30681009f0edd6211231': CoingeckoIDS.LUNA,
        '0xfb21b70922b9f6e3c6274bcd6cb1aa8a0fe20b80': CoingeckoIDS.UST,
    },
    'aurora': {
        '0xd80d8688b02b3fd3afb81cdb124f188bb5ad0445': CoingeckoIDS.SYN,
        '0xb12bfca5a55806aaf64e99521918a4bf0fc40802': CoingeckoIDS.USDC,
        '0x4988a896b1227218e4a686fde5eabdcabd91571f': CoingeckoIDS.USDT,
        '0xb1da21b0531257a7e5aefa0cd3cbf23afc674ce1': CoingeckoIDS.UST,
    },
    'moonbeam': {
        '0xf44938b0125a6662f9536281ad2cd6c499f22004': CoingeckoIDS.SYN,
        '0x0db6729c03c85b0708166ca92801bcb5cac781fc': CoingeckoIDS.SOLAR,
        '0xd2666441443daa61492ffe0f37717578714a4521': CoingeckoIDS.GOHM,
        '0xdd47a348ab60c61ad6b60ca8c31ea5e00ebfab4f': CoingeckoIDS.FRAX,
        '0x3192ae73315c3634ffa217f71cf6cbc30fee349a': CoingeckoIDS.ETH,
        '0xbf180c122d85831dcb55dc673ab47c8ab9bcefb4': CoingeckoIDS.ETH,
        '0x1d4c2a246311bb9f827f4c768e277ff5787b7d7e': CoingeckoIDS.MOVR,
        '0xa1f8890e39b4d8e33efe296d698fe42fb5e59cc3': CoingeckoIDS.AVAX,
        '0x5cf84397944b9554a278870b510e86667681ff8d': CoingeckoIDS.UST,
    },
    'cronos': {
        '0xfd0f80899983b8d46152aa1717d76cba71a31616': CoingeckoIDS.SYN,
        '0xbb0a63a6ca2071c6c4bcac11a1a317b20e3e999c': CoingeckoIDS.GOHM,
    },
    'metis': {
        '0xfb21b70922b9f6e3c6274bcd6cb1aa8a0fe20b80': CoingeckoIDS.GOHM,
        '0x67c10c397dd0ba417329543c1a40eb48aaa7cd00': CoingeckoIDS.SYN,
        '0xea32a96608495e54156ae48931a7c20f0dcc1a21': CoingeckoIDS.USDC,
        '0x931b8f17764362a3325d30681009f0edd6211231': CoingeckoIDS.ETH,
        '0x420000000000000000000000000000000000000a': CoingeckoIDS.ETH,
        '0x0b5740c6b4a97f90ef2f0220651cca420b868ffb': CoingeckoIDS.UST,
    },
    'dfk': {
        '0xb57b60debdb0b8172bb6316a9164bd3c695f133a': CoingeckoIDS.AVAX,
        '0xccb93dabd71c8dad03fc4ce5559dc3d89f67a260': CoingeckoIDS.JEWEL,
        '0x9596a3c6a4b2597adcc5d6d69b281a7c49e3fe6a': CoingeckoIDS.ETH,
        '0x77f2656d04e158f915bc22f07b779d94c1dc47ff': CoingeckoIDS.XJEWEL,
        '0xb6b5c854a8f71939556d4f3a2e5829f7fcc1bf2a': CoingeckoIDS.SYN,
        '0x3ad9dfe640e1a9cc1d9b0948620820d975c3803a': CoingeckoIDS.USDC,
        '0x360d6dd540e3448371876662fbe7f1acaf08c5ab': CoingeckoIDS.UST,
    },
}


# Fetch prices from cache but DO NOT actually cache responses.
@redis_cache(filter=lambda _: False)
def get_historic_price(_id: CoingeckoIDS,
                       date: str,
                       currency: str = "usd") -> Decimal:
    # If this function is running here, price has not been indexed yet by
    # the worker. Data should be returned by `redis_cache()`
    if POPULATE_CACHE:
        return Decimal()

    MESSAGE_QUEUE_REDIS.sadd(
        'prices:missing', *[
            _serialize_args_to_str(_id, date, currency),
            _serialize_args_to_str(_id, date)
        ])

    _date = dateutil.parser.parse(date)
    for date in date_range(_date, _date - timedelta(days=7)):
        _key = _serialize_args_to_str(_id, date)
        keys = [_key, f'{_key}:usd']

        for key in keys:
            if (data := REDIS.get(key)) is not None:
                # NOTE: data could be 0.
                return Decimal(data)
            else:
                MESSAGE_QUEUE_REDIS.sadd('prices:missing', key)

    # Did not converge, just fallback to 0.
    logging.warning(f'returned 0 for {_id} @ {date}')
    return Decimal()


def get_historic_price_syn(date: str, currency: str = "usd") -> Decimal:
    dt = dateutil.parser.parse(date)

    # SYN price didn't exist here on CG but was pegged 1:2.5 to NRV.
    if dt < datetime(year=2021, month=8, day=30):
        return get_historic_price(CoingeckoIDS.NRV, date,
                                  currency) / Decimal('2.5')

    return get_historic_price(CoingeckoIDS.SYN, date, currency)


def get_historic_price_for_address(chain: str, address: str,
                                   date: str) -> Decimal:
    if address in CUSTOM[chain]:
        return Decimal(CUSTOM[chain][address])
    elif address not in ADDRESS_TO_CGID[chain]:
        # TODO(blaze): Should trigger something to parent functions to not
        # cache this response.
        logger.warning(f'returning amount 0 for token {address} on {chain}')
        return Decimal(0)
    elif ADDRESS_TO_CGID[chain][address] == CoingeckoIDS.SYN:
        return get_historic_price_syn(date)

    return get_historic_price(ADDRESS_TO_CGID[chain][address], date)


def get_price_for_address(chain: str, address: str) -> Decimal:
    if address in CUSTOM[chain]:
        return Decimal(CUSTOM[chain][address])
    elif address not in ADDRESS_TO_CGID[chain]:
        logger.warning(f'returning amount 0 for token {address} on {chain}')
        return Decimal(0)

    return get_price_coingecko(ADDRESS_TO_CGID[chain][address])


def get_price_coingecko(_id: CoingeckoIDS, currency: str = "usd") -> Decimal:
    # Proxy method for get_historic_price() with `_date` as today.
    return get_historic_price(_id, datetime.now().date().isoformat(), currency)

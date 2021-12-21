from typing import Any, Dict, List, Union, Tuple

from web3 import Web3
from web3.contract import Contract
from web3.types import LogReceipt, TxReceipt

from data import CHAINS, BRIDGE_CONFIG, EVENTS_IN, GLOBAL_MAP
from utils.helpers import print_over, hex_to_int


def get_last_block(chain) -> int:
    w3: Web3 = CHAINS[chain]['w3']
    return w3.eth.block_number

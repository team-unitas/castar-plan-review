"""The treasury wallet: signing and sending its transactions."""

from web3 import Web3

import alchemy
import config

ERC20_ABI = [{
    "name": "transfer",
    "type": "function",
    "stateMutability": "nonpayable",
    "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}],
    "outputs": [{"name": "", "type": "bool"}],
}]


def web3(chain):
    return Web3(Web3.HTTPProvider(alchemy.url(chain)))


def token(chain, symbol):
    """A token's contract address, checksummed."""
    return Web3.to_checksum_address(config.TOKENS[(chain, symbol)][0])


def send(chain, call):
    """Sign a contract call from the treasury and broadcast it. Returns the tx hash without waiting."""
    w3 = web3(chain)
    sender = Web3.to_checksum_address(config.TREASURY_ADDRESS)
    tx = call.build_transaction(
        {"from": sender, "nonce": w3.eth.get_transaction_count(sender, "pending")}
    )
    signed = w3.eth.account.sign_transaction(tx, config.TREASURY_PRIVATE_KEY)
    return Web3.to_hex(w3.eth.send_raw_transaction(signed.raw_transaction))


def pay(chain, symbol, to, amount):
    """Send amount (base units) of a token from the treasury to `to`. Returns the tx hash."""
    contract = web3(chain).eth.contract(address=token(chain, symbol), abi=ERC20_ABI)
    return send(chain, contract.functions.transfer(Web3.to_checksum_address(to), amount))


def wait(chain, tx_hash):
    """Block until the transaction is mined. Raises if it reverted."""
    receipt = web3(chain).eth.wait_for_transaction_receipt(tx_hash, timeout=600)
    if receipt["status"] != 1:
        raise RuntimeError(f"transaction {tx_hash} reverted")

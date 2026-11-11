"""Quotes and swaps on Uniswap v3, from the treasury and back into it.

The treasury has a standing approval for the router on every token (ops set
it up once), so a swap is a single transaction.
"""

from web3 import Web3

import config
import treasury

QUOTER_ABI = [{
    "name": "quoteExactInputSingle",
    "type": "function",
    "stateMutability": "nonpayable",
    "inputs": [{"name": "params", "type": "tuple", "components": [
        {"name": "tokenIn", "type": "address"},
        {"name": "tokenOut", "type": "address"},
        {"name": "amountIn", "type": "uint256"},
        {"name": "fee", "type": "uint24"},
        {"name": "sqrtPriceLimitX96", "type": "uint160"},
    ]}],
    "outputs": [
        {"name": "amountOut", "type": "uint256"},
        {"name": "sqrtPriceX96After", "type": "uint160"},
        {"name": "initializedTicksCrossed", "type": "uint32"},
        {"name": "gasEstimate", "type": "uint256"},
    ],
}]

ROUTER_ABI = [{
    "name": "exactInputSingle",
    "type": "function",
    "stateMutability": "payable",
    "inputs": [{"name": "params", "type": "tuple", "components": [
        {"name": "tokenIn", "type": "address"},
        {"name": "tokenOut", "type": "address"},
        {"name": "fee", "type": "uint24"},
        {"name": "recipient", "type": "address"},
        {"name": "amountIn", "type": "uint256"},
        {"name": "amountOutMinimum", "type": "uint256"},
        {"name": "sqrtPriceLimitX96", "type": "uint160"},
    ]}],
    "outputs": [{"name": "amountOut", "type": "uint256"}],
}]


def quote(chain, token_in, token_out, amount_in):
    """How much token_out a swap of amount_in would return right now. Base units."""
    quoter = treasury.web3(chain).eth.contract(
        address=Web3.to_checksum_address(config.UNISWAP[chain]["quoter"]), abi=QUOTER_ABI
    )
    amount_out, _, _, _ = quoter.functions.quoteExactInputSingle((
        treasury.token(chain, token_in),
        treasury.token(chain, token_out),
        amount_in,
        config.POOL_FEE,
        0,  # no price limit
    )).call()
    return amount_out


def swap(chain, token_in, token_out, amount_in, min_amount_out):
    """Swap amount_in of token_in from the treasury for token_out, paid into the treasury.

    The swap reverts unless it returns at least min_amount_out. Returns the
    tx hash without waiting.
    """
    router = treasury.web3(chain).eth.contract(
        address=Web3.to_checksum_address(config.UNISWAP[chain]["router"]), abi=ROUTER_ABI
    )
    return treasury.send(chain, router.functions.exactInputSingle((
        treasury.token(chain, token_in),
        treasury.token(chain, token_out),
        config.POOL_FEE,
        Web3.to_checksum_address(config.TREASURY_ADDRESS),
        amount_in,
        min_amount_out,
        0,  # no price limit
    )))

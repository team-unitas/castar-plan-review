"""Settings, and the chains, tokens and Uniswap contracts we use."""

import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/castar_conversions")
ALCHEMY_API_KEY = os.environ.get("ALCHEMY_API_KEY", "")

# Castar's treasury wallet. Every deposit lands here, and every swap and
# payout is sent from here. The same address on both chains, lowercase.
TREASURY_ADDRESS = os.environ.get("TREASURY_ADDRESS", "").lower()
TREASURY_PRIVATE_KEY = os.environ.get("TREASURY_PRIVATE_KEY", "")  # a KMS signer in a real deployment

# Our chain name -> Alchemy network slug.
CHAINS = {
    "ethereum": "eth-mainnet",
    "base": "base-mainnet",
}

# (chain, symbol) -> (token contract, decimals). Addresses are lowercase.
# Every amount in this service is an integer number of base units.
TOKENS = {
    ("ethereum", "USDC"): ("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", 6),
    ("ethereum", "USDT"): ("0xdac17f958d2ee523a2206206994597c13d831ec7", 6),
    ("ethereum", "DAI"): ("0x6b175474e89094c44da98b954eedeac495271d0f", 18),
    ("base", "USDC"): ("0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", 6),
    ("base", "DAI"): ("0x50c5725949a6f0c72e6c4a641f24049a917db0cb", 18),
}

# Uniswap v3 contracts on each chain.
UNISWAP = {
    "ethereum": {
        "router": "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45",  # SwapRouter02
        "quoter": "0x61ffe014ba17989e743c5f6cb21bf9697530b21e",  # QuoterV2
    },
    "base": {
        "router": "0x2626664c2603336e57b271c5c0b26f421741e481",
        "quoter": "0x3d4e44eb1374240ce5f1b871ab261cd16335b76a",
    },
}
POOL_FEE = 100  # every stable pair trades in its 0.01% pool

FEE_BPS = 10  # Castar's fee: 0.10% of the quoted output

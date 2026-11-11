"""Calls to Alchemy, our only node provider."""

import requests

import config


def url(chain):
    return f"https://{config.CHAINS[chain]}.g.alchemy.com/v2/{config.ALCHEMY_API_KEY}"


def rpc(chain, method, params):
    resp = requests.post(
        url(chain),
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=10,
    )
    resp.raise_for_status()
    body = resp.json()
    if "error" in body:
        raise RuntimeError(f"{method} failed: {body['error']}")
    return body["result"]


def token_balances(chain, address, contracts):
    """Current base-unit balance of each token contract at address, keyed by contract."""
    result = rpc(chain, "alchemy_getTokenBalances", [address, contracts])
    return {
        b["contractAddress"].lower(): int(b["tokenBalance"], 16)
        for b in result["tokenBalances"]
    }

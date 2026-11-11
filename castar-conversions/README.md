# castar-conversions (toy)

A deliberately tiny version of Castar's conversions service, written for this
interview. It cuts corners on purpose: plain API keys, no request schemas, no
migrations, no retries. It keeps only what you need to follow the plan you'll
review in the interview.

## What it does

Customers convert one stablecoin into another, on Ethereum or Base. Ops
registers each customer's wallets (there's no endpoint for that here).
Customers call the API directly, or through Castar's web dashboard, which uses
the same endpoints.

- **`GET /wallets/<id>/balances`** returns a wallet's token balances, read live
  from Alchemy.
- **`POST /conversions`** opens a conversion. Castar quotes the swap on Uniswap
  and fixes the payout (`dest_amount`): the quote, less Castar's 0.10% fee. The
  response says where to send the funds (`deposit_address`, which is Castar's
  treasury) and how much (`amount`).
- **`GET /conversions/<id>`** returns one conversion.

A conversion runs like this:

1. The customer sends `amount` of the source asset from their source wallet to
   the treasury.
2. Castar swaps it on Uniswap, into the treasury.
3. Castar pays `dest_amount` of the destination asset from the treasury into the
   customer's recipient wallet, on the same chain.

The treasury is one address on both chains. It holds every customer's
deposits and Castar's own inventory, so nothing on chain says which tokens
belong to which conversion; our database does.

**Today, steps 2 and 3 are run by hand.** Ops watches the treasury on Etherscan
and Basescan. When a deposit arrives, they check that it came from the
conversion's source wallet, in the source asset, for the full `amount`. Then
they run `flask settle <conversion id>`, which sends the swap, waits for it,
sends the payout and waits for that.

## Files

| File | What's in it |
|---|---|
| `app.py` | The HTTP API, and the `settle` command ops runs |
| `models.py` | `Customer`, `Wallet`, `Conversion` |
| `uniswap.py` | Quotes and swaps on Uniswap v3 |
| `treasury.py` | Signing and sending the treasury's transactions |
| `alchemy.py` | JSON-RPC calls to Alchemy |
| `config.py` | Settings, and the chains, tokens and contracts we use |

## Example

Convert 250,000 USDT into USDC on Ethereum. Wallets 7 and 8 are two of the
customer's Ethereum wallets. Amounts are integer base units: USDT and USDC have
6 decimals, and DAI has 18.

```bash
curl -s -X POST localhost:5000/conversions \
  -H "Authorization: Bearer $KEY" -H "Idempotency-Key: payout-2026-11-03" \
  -H "Content-Type: application/json" \
  -d '{"source_wallet_id": 7, "recipient_wallet_id": 8,
       "source_asset": "USDT", "dest_asset": "USDC", "amount": "250000000000"}'
```

Uniswap quotes 249,975 USDC, so the payout is fixed at 249,725.025 USDC:

```json
{
  "id": "5c1e9a0e-3f7b-4c8e-9d61-0b2f4a7e8c13",
  "status": "awaiting_deposit",
  "network": "ethereum",
  "source_wallet_id": 7,
  "recipient_wallet_id": 8,
  "source_asset": "USDT",
  "dest_asset": "USDC",
  "amount": "250000000000",
  "dest_amount": "249725025000",
  "deposit_address": "0x9c1e5b7f3a0d2c84e6b1f07a5d3c9e28b4a6f011",
  "swap_tx_hash": null,
  "payout_tx_hash": null,
  "created_at": "2026-11-03T14:02:11+00:00"
}
```

## Running it

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://localhost/castar_conversions ALCHEMY_API_KEY=...
export TREASURY_ADDRESS=... TREASURY_PRIVATE_KEY=...
flask --app app init-db
flask --app app run
flask --app app settle <conversion id>   # ops, after checking a deposit
```

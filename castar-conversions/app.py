"""castar-conversions: wallet balances and conversions."""

import click
from flask import Flask, abort, g, jsonify, request
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

import alchemy
import config
import treasury
import uniswap
from models import Conversion, Customer, Wallet, db

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = config.DATABASE_URL
db.init_app(app)


@app.errorhandler(HTTPException)
def json_error(e):
    return jsonify(error=e.description), e.code


@app.before_request
def authenticate():
    key = request.headers.get("Authorization", "").removeprefix("Bearer ")
    g.customer = Customer.query.filter_by(api_key=key).first()
    if g.customer is None:
        abort(401, "invalid API key")


def own_wallet(wallet_id):
    wallet = db.session.get(Wallet, wallet_id)
    if wallet is None or wallet.customer_id != g.customer.id:
        abort(404, "wallet not found")
    return wallet


@app.get("/wallets/<int:wallet_id>/balances")
def wallet_balances(wallet_id):
    """The wallet's token balances, read live from Alchemy."""
    wallet = own_wallet(wallet_id)
    tokens = {
        symbol: contract
        for (chain, symbol), (contract, _decimals) in config.TOKENS.items()
        if chain == wallet.network
    }
    amounts = alchemy.token_balances(wallet.network, wallet.address, list(tokens.values()))
    return jsonify(
        wallet_id=wallet.id,
        network=wallet.network,
        balances={symbol: str(amounts[contract]) for symbol, contract in tokens.items()},
    )


@app.post("/conversions")
def create_conversion():
    key = request.headers.get("Idempotency-Key")
    if not key:
        abort(400, "Idempotency-Key header required")
    existing = Conversion.query.filter_by(customer_id=g.customer.id, idempotency_key=key).first()
    if existing is not None:
        return jsonify(existing.to_dict())

    body = request.get_json()
    source = own_wallet(body["source_wallet_id"])
    recipient = own_wallet(body["recipient_wallet_id"])
    if source.network != recipient.network:
        abort(422, "source and recipient wallets must be on the same chain")
    chain = source.network
    source_asset = body["source_asset"].upper()
    dest_asset = body["dest_asset"].upper()
    for symbol in (source_asset, dest_asset):
        if (chain, symbol) not in config.TOKENS:
            abort(422, f"{symbol} is not supported on {chain}")
    if source_asset == dest_asset:
        abort(422, "source_asset and dest_asset must differ")
    amount = int(body["amount"])
    if amount <= 0:
        abort(422, "amount must be positive")

    # The payout is fixed now: what the swap would return today, less our fee.
    quoted = uniswap.quote(chain, source_asset, dest_asset, amount)
    conv = Conversion(
        customer_id=g.customer.id,
        idempotency_key=key,
        source_wallet_id=source.id,
        recipient_wallet_id=recipient.id,
        network=chain,
        source_asset=source_asset,
        dest_asset=dest_asset,
        amount=amount,
        dest_amount=quoted * (10_000 - config.FEE_BPS) // 10_000,
        deposit_address=config.TREASURY_ADDRESS,
    )
    db.session.add(conv)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, f"wallet {source.id} already has a {source_asset} conversion awaiting a deposit")
    return jsonify(conv.to_dict()), 201


@app.get("/conversions/<conversion_id>")
def get_conversion(conversion_id):
    conv = db.session.get(Conversion, conversion_id)
    if conv is None or conv.customer_id != g.customer.id:
        abort(404, "conversion not found")
    return jsonify(conv.to_dict())


@app.cli.command("init-db")
def init_db():
    db.create_all()


@app.cli.command("settle")
@click.argument("conversion_id")
def settle(conversion_id):
    """Swap and pay out a conversion whose deposit ops has checked by hand."""
    conv = db.session.get(Conversion, conversion_id)
    if conv is None or conv.status != "awaiting_deposit":
        raise click.ClickException("no conversion awaiting a deposit has that id")
    recipient = db.session.get(Wallet, conv.recipient_wallet_id)

    # The swap reverts rather than return less than we promised to pay out.
    conv.swap_tx_hash = uniswap.swap(
        conv.network,
        conv.source_asset,
        conv.dest_asset,
        amount_in=int(conv.amount),
        min_amount_out=int(conv.dest_amount),
    )
    conv.status = "swapping"
    db.session.commit()
    treasury.wait(conv.network, conv.swap_tx_hash)

    conv.payout_tx_hash = treasury.pay(
        conv.network, conv.dest_asset, recipient.address, int(conv.dest_amount)
    )
    conv.status = "paying_out"
    db.session.commit()
    treasury.wait(conv.network, conv.payout_tx_hash)

    conv.status = "completed"
    db.session.commit()
    click.echo(f"swap {conv.swap_tx_hash}, payout {conv.payout_tx_hash}")

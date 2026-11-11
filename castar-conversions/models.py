import uuid
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc)


class Customer(db.Model):
    __tablename__ = "customers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    api_key = db.Column(db.String(64), unique=True, nullable=False)  # hashed in a real deployment


class Wallet(db.Model):
    """A customer's wallet, registered by ops. A conversion sends from one and pays into one."""

    __tablename__ = "wallets"
    __table_args__ = (db.UniqueConstraint("customer_id", "network", "address"),)
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.ForeignKey("customers.id"), nullable=False)
    network = db.Column(db.String(16), nullable=False)  # a key of config.CHAINS
    address = db.Column(db.String(42), nullable=False)  # lowercase


# Conversion statuses:
#   awaiting_deposit  waiting for the customer to send `amount` to the treasury
#   swapping          swap sent; waiting for it to be mined
#   paying_out        payout sent; waiting for it to be mined
#   completed         the payout is mined


class Conversion(db.Model):
    """Convert source_asset into dest_asset, on one chain.

    The customer sends `amount` of source_asset from their source wallet to
    the treasury. Castar swaps it on Uniswap, then pays `dest_amount` of
    dest_asset from the treasury into the recipient wallet.
    """

    __tablename__ = "conversions"
    __table_args__ = (
        db.UniqueConstraint("customer_id", "idempotency_key"),
        # Every deposit lands in the same treasury address, so deposits can
        # only be told apart by who sent them and in which token. At most one
        # conversion per source wallet and asset may be awaiting a deposit.
        db.Index(
            "uq_conversions_awaiting_deposit",
            "source_wallet_id",
            "source_asset",
            unique=True,
            postgresql_where=db.text("status = 'awaiting_deposit'"),
        ),
    )
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.ForeignKey("customers.id"), nullable=False)
    idempotency_key = db.Column(db.String(128), nullable=False)
    source_wallet_id = db.Column(db.ForeignKey("wallets.id"), nullable=False)
    recipient_wallet_id = db.Column(db.ForeignKey("wallets.id"), nullable=False)
    network = db.Column(db.String(16), nullable=False)  # both wallets' chain
    source_asset = db.Column(db.String(8), nullable=False)  # e.g. "USDT"
    dest_asset = db.Column(db.String(8), nullable=False)  # e.g. "USDC"
    # Base units of source_asset the customer must send.
    amount = db.Column(db.Numeric(78, 0), nullable=False)
    # Base units of dest_asset we pay out: the Uniswap quote at creation, less
    # our fee. Fixed when the conversion is created.
    dest_amount = db.Column(db.Numeric(78, 0), nullable=False)
    deposit_address = db.Column(db.String(42), nullable=False)  # the treasury, lowercase
    status = db.Column(db.String(32), nullable=False, default="awaiting_deposit")
    swap_tx_hash = db.Column(db.String(66))
    payout_tx_hash = db.Column(db.String(66))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "network": self.network,
            "source_wallet_id": self.source_wallet_id,
            "recipient_wallet_id": self.recipient_wallet_id,
            "source_asset": self.source_asset,
            "dest_asset": self.dest_asset,
            "amount": str(self.amount),
            "dest_amount": str(self.dest_amount),
            "deposit_address": self.deposit_address,
            "swap_tx_hash": self.swap_tx_hash,
            "payout_tx_hash": self.payout_tx_hash,
            "created_at": self.created_at.isoformat(),
        }

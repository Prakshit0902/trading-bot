from __future__ import annotations

import re
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class OrderRequest(BaseModel):
    """
    Pydantic model representing a Binance futures order request.
    Validates symbol, side, order_type, quantity, price, etc.
    """
    symbol: str
    side: Literal["BUY", "SELL"]
    order_type: Literal["MARKET", "LIMIT", "STOP_MARKET"]
    quantity: Decimal
    price: Decimal | None = None
    stop_price: Decimal | None = None
    time_in_force: str | None = None
    client_order_id: str | None = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.fullmatch(r"^[A-Z0-9]+$", v):
            raise ValueError("Symbol must contain only letters and numbers, for example BTCUSDT.")
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Quantity must be greater than zero.")
        return v

    @field_validator("price", "stop_price")
    @classmethod
    def validate_price(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("Price must be greater than zero.")
        return v

    def to_api_payload(self) -> dict[str, str]:
        """Convert the validated model into a dictionary suitable for the Binance API."""
        payload = {
            "symbol": self.symbol,
            "side": self.side,
            "type": self.order_type,
            "quantity": format(self.quantity, "f"),
            "newOrderRespType": "RESULT",
        }

        if self.price is not None:
            payload["price"] = format(self.price, "f")

        if self.stop_price is not None:
            payload["stopPrice"] = format(self.stop_price, "f")

        if self.time_in_force is not None:
            payload["timeInForce"] = self.time_in_force

        if self.client_order_id is not None:
            payload["newClientOrderId"] = self.client_order_id

        return payload

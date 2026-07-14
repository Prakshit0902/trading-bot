from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import uuid4

from bot.client import BinanceFuturesTestnetClient
from bot.models import OrderRequest


def build_market_order(symbol: str, side: str, quantity: Decimal, client_order_id: str | None = None) -> OrderRequest:
    return OrderRequest(
        symbol=symbol,
        side=side,
        order_type="MARKET",
        quantity=quantity,
        client_order_id=client_order_id or f"tbm-{uuid4().hex[:20]}",
    )


def build_limit_order(
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    time_in_force: str = "GTC",
    client_order_id: str | None = None,
) -> OrderRequest:
    return OrderRequest(
        symbol=symbol,
        side=side,
        order_type="LIMIT",
        quantity=quantity,
        price=price,
        time_in_force=time_in_force,
        client_order_id=client_order_id or f"tbl-{uuid4().hex[:20]}",
    )


def build_stop_market_order(
    symbol: str,
    side: str,
    quantity: Decimal,
    stop_price: Decimal,
    client_order_id: str | None = None,
) -> OrderRequest:
    return OrderRequest(
        symbol=symbol,
        side=side,
        order_type="STOP_MARKET",
        quantity=quantity,
        stop_price=stop_price,
        client_order_id=client_order_id or f"tbsm-{uuid4().hex[:19]}",
    )

class OrderService:
    def __init__(self, client: BinanceFuturesTestnetClient, logger: logging.Logger | None = None) -> None:
        self.client = client
        self.logger = logger or logging.getLogger(__name__)

    def submit(self, order: OrderRequest) -> dict[str, Any]:
        payload = order.to_api_payload()
        self.logger.info("Submitting order payload: %s", self._safe_payload(payload))
        response = self.client.place_order(payload)
        self.logger.info("Order accepted by Binance: %s", self._safe_payload(response))
        return response

    def _safe_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        safe_payload = dict(payload)
        safe_payload.pop("signature", None)
        return safe_payload

from __future__ import annotations

import unittest
from decimal import Decimal

from bot.orders import build_limit_order, build_market_order, build_stop_market_order
from bot.models import OrderRequest
from pydantic import ValidationError


class OrderTests(unittest.TestCase):
    def test_market_order_payload(self) -> None:
        order = build_market_order("BTCUSDT", "BUY", Decimal("0.001"), client_order_id="abc123")
        payload = order.to_api_payload()

        self.assertEqual(payload["symbol"], "BTCUSDT")
        self.assertEqual(payload["side"], "BUY")
        self.assertEqual(payload["type"], "MARKET")
        self.assertEqual(payload["quantity"], "0.001")
        self.assertEqual(payload["newClientOrderId"], "abc123")

    def test_limit_order_payload(self) -> None:
        order = build_limit_order("BTCUSDT", "SELL", Decimal("0.001"), Decimal("75000"), client_order_id="xyz789")
        payload = order.to_api_payload()

        self.assertEqual(payload["type"], "LIMIT")
        self.assertEqual(payload["price"], "75000")
        self.assertEqual(payload["timeInForce"], "GTC")
        self.assertEqual(payload["newClientOrderId"], "xyz789")

    def test_stop_market_order_payload(self) -> None:
        order = build_stop_market_order("BTCUSDT", "SELL", Decimal("0.001"), Decimal("70000"), client_order_id="sm123")
        payload = order.to_api_payload()
        
        self.assertEqual(payload["type"], "STOP_MARKET")
        self.assertEqual(payload["stopPrice"], "70000")
        self.assertEqual(payload["newClientOrderId"], "sm123")

    def test_order_request_defaults(self) -> None:
        order = OrderRequest(symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity=Decimal("0.001"))
        payload = order.to_api_payload()

        self.assertNotIn("price", payload)
        self.assertNotIn("timeInForce", payload)

    def test_pydantic_validation(self) -> None:
        with self.assertRaises(ValidationError):
            OrderRequest(symbol="btc-usdt", side="BUY", order_type="MARKET", quantity=Decimal("1"))
            
        with self.assertRaises(ValidationError):
            OrderRequest(symbol="BTCUSDT", side="HOLD", order_type="MARKET", quantity=Decimal("1"))
            
        with self.assertRaises(ValidationError):
            OrderRequest(symbol="BTCUSDT", side="BUY", order_type="MARKET", quantity=Decimal("-1"))


if __name__ == "__main__":
    unittest.main()

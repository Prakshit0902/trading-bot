from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

import requests


class BinanceAPIError(RuntimeError):
    """Raised when Binance returns a non-success response."""

    def __init__(self, message: str, status_code: int | None = None, code: int | None = None, payload: Any | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.payload = payload


@dataclass(slots=True)
class BinanceFuturesTestnetClient:
    api_key: str
    api_secret: str
    base_url: str = "https://testnet.binancefuture.com"
    recv_window: int = 5000

    @classmethod
    def from_env(cls) -> "BinanceFuturesTestnetClient":
        api_key = os.getenv("BINANCE_API_KEY") or os.getenv("BINANCE_TESTNET_API_KEY") or os.getenv("API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET") or os.getenv("BINANCE_TESTNET_API_SECRET") or os.getenv("API_SECRET")
        base_url = os.getenv("BINANCE_BASE_URL", "https://testnet.binancefuture.com")

        if not api_key or not api_secret:
            raise RuntimeError("Missing Binance credentials. Set BINANCE_API_KEY and BINANCE_API_SECRET in your environment.")

        return cls(api_key=api_key, api_secret=api_secret, base_url=base_url.rstrip("/"))

    def place_order(self, order_params: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/fapi/v1/order", order_params, signed=True)

    def get_server_time(self) -> dict[str, Any]:
        return self._request("GET", "/fapi/v1/time")

    def get_ticker_price(self, symbol: str) -> Decimal:
        """Fetch the current price for a symbol."""
        response = self._request("GET", "/fapi/v1/ticker/price", {"symbol": symbol})
        price_str = response.get("price")
        if not price_str:
            raise BinanceAPIError(f"Could not find price for symbol {symbol} in response.")
        return Decimal(price_str)

    def _request(self, method: str, path: str, params: dict[str, Any] | None = None, signed: bool = False) -> dict[str, Any]:
        request_params = self._prepare_params(params or {})
        if signed:
            request_params["timestamp"] = int(time.time() * 1000)
            request_params["recvWindow"] = self.recv_window
            request_params["signature"] = self._sign_params(request_params)

        url = f"{self.base_url}{path}"
        headers = {
            "X-MBX-APIKEY": self.api_key,
            "Accept": "application/json",
        }

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=request_params if method.upper() == "GET" else None,
                data=request_params if method.upper() != "GET" else None,
                timeout=20,
            )
        except requests.RequestException as exc:
            raise BinanceAPIError(f"Network error while calling Binance: {exc}") from exc

        if response.ok:
            if not response.text:
                return {}
            try:
                return response.json()
            except ValueError as exc:
                raise BinanceAPIError("Binance returned a non-JSON response.", status_code=response.status_code, payload=response.text) from exc

        payload = self._decode_payload(response)
        error_code = payload.get("code") if isinstance(payload, dict) else None
        error_message = payload.get("msg") if isinstance(payload, dict) else response.text
        raise BinanceAPIError(
            f"Binance request failed with HTTP {response.status_code}: {error_message}",
            status_code=response.status_code,
            code=error_code,
            payload=payload,
        )

    def _sign_params(self, params: dict[str, Any]) -> str:
        query_string = urlencode(self._stringify_params(params))
        signature = hmac.new(self.api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()
        return signature

    def _prepare_params(self, params: dict[str, Any]) -> dict[str, Any]:
        prepared: dict[str, Any] = {}
        for key, value in params.items():
            if value is None:
                continue
            if isinstance(value, Decimal):
                prepared[key] = format(value, "f")
            elif isinstance(value, bool):
                prepared[key] = "true" if value else "false"
            else:
                prepared[key] = value
        return prepared

    def _stringify_params(self, params: dict[str, Any]) -> dict[str, str]:
        return {key: str(value) for key, value in params.items()}

    def _decode_payload(self, response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return response.text

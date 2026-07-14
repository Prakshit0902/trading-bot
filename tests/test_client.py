import pytest
import responses
from decimal import Decimal
from bot.client import BinanceFuturesTestnetClient, BinanceAPIError

@pytest.fixture
def client():
    return BinanceFuturesTestnetClient(api_key="test_key", api_secret="test_secret")

@responses.activate
def test_get_ticker_price_success(client):
    responses.add(
        responses.GET,
        "https://testnet.binancefuture.com/fapi/v1/ticker/price?symbol=BTCUSDT",
        json={"symbol": "BTCUSDT", "price": "75000.50", "time": 1690000000000},
        status=200
    )
    
    price = client.get_ticker_price("BTCUSDT")
    assert price == Decimal("75000.50")

@responses.activate
def test_get_ticker_price_not_found(client):
    responses.add(
        responses.GET,
        "https://testnet.binancefuture.com/fapi/v1/ticker/price?symbol=INVALID",
        json={"code": -1121, "msg": "Invalid symbol."},
        status=400
    )
    
    with pytest.raises(BinanceAPIError) as exc_info:
        client.get_ticker_price("INVALID")
    
    assert exc_info.value.status_code == 400
    assert "Invalid symbol" in str(exc_info.value)

@responses.activate
def test_place_order_success(client):
    responses.add(
        responses.POST,
        "https://testnet.binancefuture.com/fapi/v1/order",
        json={"orderId": 123456, "symbol": "BTCUSDT", "status": "NEW"},
        status=200
    )
    
    response = client.place_order({
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "MARKET",
        "quantity": "0.001"
    })
    
    assert response["orderId"] == 123456
    assert response["status"] == "NEW"

@responses.activate
def test_place_order_auth_failure(client):
    responses.add(
        responses.POST,
        "https://testnet.binancefuture.com/fapi/v1/order",
        json={"code": -2015, "msg": "Invalid API-key, IP, or permissions for action."},
        status=401
    )
    
    with pytest.raises(BinanceAPIError) as exc_info:
        client.place_order({"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": "0.001"})
        
    assert exc_info.value.status_code == 401
    assert exc_info.value.code == -2015

import pytest
from unittest.mock import MagicMock, patch
from modules.trader import Trader
import time
import asyncio

# ------------------------- Fixtures ------------------------- #

@pytest.fixture
def trader():
    return Trader(
        api_key="test_api_key",
        secret_key="test_secret_key",
        base_url="https://mock.api.lbank.info"
    )

@pytest.fixture
def mock_response():
    return {
        "result": True,
        "order_id": "12345",
        "custom_id": "67890"
    }

# ------------------------- Tests ------------------------- #

def test_generate_signature(trader):
    params = {"symbol": "BTC_USDT", "amount": "0.1"}
    signature = trader._generate_signature(params)
    
    assert isinstance(signature, str)
    assert len(signature) == 32  # MD5 hash length

@patch('requests.post')
def test_private_post(mock_post, trader, mock_response):
    mock_post.return_value.json.return_value = mock_response
    
    endpoint = "/v2/test_endpoint.do"
    params = {"param1": "value1"}
    result = trader._private_post(endpoint, params)
    
    assert result == mock_response
    mock_post.assert_called_once()

@patch('modules.trader.Trader._private_post')
def test_place_order_limit_buy(mock_private_post, trader, mock_response):
    mock_private_post.return_value = mock_response
    
    result = trader.place_order(
        symbol="BTC_USDT",
        side="buy",
        amount=0.1,
        price=50000
    )
    
    assert result == mock_response
    assert "12345" in trader._open

@patch('modules.trader.Trader._private_post')
def test_place_order_market_sell(mock_private_post, trader, mock_response):
    mock_private_post.return_value = mock_response
    
    result = trader.place_order(
        symbol="BTC_USDT",
        side="sell",
        amount=0.1,
        order_style="market"
    )
    
    assert result == mock_response
    assert "type" in mock_private_post.call_args[1]["params"]
    assert "sell_market" in mock_private_post.call_args[1]["params"]["type"]

@patch('modules.trader.Trader._private_post')
def test_cancel_order(mock_private_post, trader):
    trader.cancel_order("BTC_USDT", "12345")
    
    mock_private_post.assert_called_once_with(
        "/v2/cancel_order.do",
        {"symbol": "BTC_USDT", "order_id": "12345"}
    )

@patch('modules.trader.Trader._private_post')
def test_get_order_info(mock_private_post, trader):
    trader.get_order_info("BTC_USDT", "12345")
    
    mock_private_post.assert_called_once_with(
        "/v2/order_info.do",
        {"symbol": "BTC_USDT", "order_id": "12345"}
    )

@pytest.mark.asyncio
@patch('modules.trader.Trader.get_order_info')
@patch('modules.trader.publish')
async def test_monitor_order_success(mock_publish, mock_get_info, trader):
    # Setup mock order info responses
    mock_get_info.side_effect = [
        {"status": "open"},  # First poll
        {"status": "filled", "price": "51000"}  # Second poll
    ]
    
    # Add a test order to monitor
    trader._open["12345"] = {
        "symbol": "BTC_USDT",
        "side": "buy",
        "entry": 50000,
        "signal_id": "67890"
    }
    
    await trader._monitor_order("12345", poll_every=0.1)
    
    # Verify publish was called with success
    assert mock_publish.called
    assert mock_publish.call_args[0][1].result == "SUCCESS"
    assert "12345" not in trader._open  # Order should be removed

@pytest.mark.asyncio
@patch('modules.trader.Trader.get_order_info')
@patch('modules.trader.publish')
async def test_monitor_order_failure(mock_publish, mock_get_info, trader):
    # Setup mock order info responses
    mock_get_info.side_effect = [
        {"status": "open"},  # First poll
        {"status": "cancelled"}  # Second poll
    ]
    
    # Add a test order to monitor
    trader._open["12345"] = {
        "symbol": "BTC_USDT",
        "side": "buy",
        "entry": 50000,
        "signal_id": "67890"
    }
    
    await trader._monitor_order("12345", poll_every=0.1)
    
    # Verify publish was called with failure
    assert mock_publish.called
    assert "12345" not in trader._open  # Order should be removed

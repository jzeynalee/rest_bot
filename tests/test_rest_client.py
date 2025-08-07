import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from modules.rest_client import RestPollingClient, RateLimiter
import aiohttp
import pandas as pd
import logging

# ------------------------- Fixtures ------------------------- #

@pytest.fixture
def mock_config():
    return {
        "SYMBOLS": ["BTC_USDT"],
        "TIMEFRAMES": ["1m", "5m"],
        "REST_TIMEFRAME_CODES": {"1m": "1min", "5m": "5min"}
    }

@pytest.fixture
def mock_data_provider():
    provider = MagicMock()
    provider.create_dataframe_from_kline.return_value = pd.DataFrame({
        'timestamp': [datetime.now().timestamp()],
        'open': [50000],
        'high': [51000],
        'low': [49000],
        'close': [50500],
        'volume': [100]
    })
    return provider

@pytest.fixture
def mock_strategy():
    strategy = MagicMock()
    strategy.generate_signal.return_value = {
        "action": "buy",
        "price": 50500,
        "confidence": 0.8
    }
    return strategy

@pytest.fixture
def mock_dispatcher():
    return MagicMock()

@pytest.fixture
def polling_client(mock_config, mock_data_provider, mock_strategy, mock_dispatcher):
    return RestPollingClient(
        config=mock_config,
        logger=logging.getLogger(),
        data_provider=mock_data_provider,
        strategy=mock_strategy,
        dispatcher=mock_dispatcher
    )

# ------------------------- Tests ------------------------- #

@pytest.mark.asyncio
async def test_rate_limiter():
    limiter = RateLimiter(max_requests_per_10s=2)
    
    # First two should pass quickly
    start = asyncio.get_event_loop().time()
    await limiter.acquire()
    await limiter.acquire()
    duration = asyncio.get_event_loop().time() - start
    assert duration < 0.1  # Should be almost instant
    
    # Third should be rate limited
    start = asyncio.get_event_loop().time()
    await limiter.acquire()
    duration = asyncio.get_event_loop().time() - start
    assert duration >= 10  # Should wait ~10 seconds

@pytest.mark.asyncio
async def test_fetch_and_process_success(polling_client):
    mock_session = AsyncMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json.return_value = {"data": "mock_kline_data"}
    mock_session.get.return_value.__aenter__.return_value = mock_response
    
    await polling_client.fetch_and_process(mock_session, "BTC_USDT", "1m")
    
    # Verify the data flow
    polling_client.data_provider.create_dataframe_from_kline.assert_called_once_with({"data": "mock_kline_data"})
    polling_client.strategy.generate_signal.assert_called_once()
    polling_client.dispatcher.send_trade_signal.assert_called()

@pytest.mark.asyncio
async def test_fetch_and_process_failure(polling_client):
    mock_session = AsyncMock()
    mock_session.get.side_effect = Exception("Mock error")
    
    initial_errors = polling_client.metrics["errors"]
    await polling_client.fetch_and_process(mock_session, "BTC_USDT", "1m")
    
    assert polling_client.metrics["errors"] == initial_errors + 1

@pytest.mark.asyncio
async def test_poll_timeframe(polling_client):
    mock_session = AsyncMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json.return_value = {"data": "mock_kline_data"}
    mock_session.get.return_value.__aenter__.return_value = mock_response
    
    await polling_client.poll_timeframe(mock_session, "1m")
    
    assert polling_client.metrics["requests_sent"] == len(polling_client.symbols)

@pytest.mark.asyncio
async def test_prefetch_all_timeframes(polling_client):
    mock_session = AsyncMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json.return_value = {"data": "mock_kline_data"}
    mock_session.get.return_value.__aenter__.return_value = mock_response
    
    with patch('aiohttp.ClientSession', return_value=mock_session):
        await polling_client.prefetch_all_timeframes()
    
    expected_calls = len(polling_client.symbols) * len(polling_client.timeframes)
    assert polling_client.metrics["requests_sent"] == expected_calls

def test_log_metrics(polling_client, caplog):
    polling_client.metrics = {
        "requests_sent": 10,
        "errors": 2,
        "latencies": [0.1, 0.2, 0.3]
    }
    
    polling_client.log_metrics()
    
    assert "Requests: 10" in caplog.text
    assert "Errors: 2" in caplog.text
    assert "Avg latency" in caplog.text

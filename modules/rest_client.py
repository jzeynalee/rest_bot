"""
rest_client.py
--------------
Polling client that fetches OHLCV via REST, enriches with indicators,
evaluates a Strategy, plans SL/TP, and dispatches a signal.
"""

from __future__ import annotations

import asyncio
import time
import logging
from collections import deque
from typing import Dict, Optional

import aiohttp
import pandas as pd

from modules.indicator import IndicatorCalculator
from modules.trade_planner import TradePlanner
from modules.data_provider import DataProvider
from notifiers.SignalDispatcher import SignalDispatcher
from modules.strategy.macd_rsi import MacdRsiStrategy  # default strategy


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #
class RateLimiter:
    """Simple sliding-window rate limiter (N requests per 10 s)."""

    def __init__(self, max_requests_per_10s: int) -> None:
        self.max_requests = max_requests_per_10s
        self.timestamps: deque[float] = deque()

    async def acquire(self) -> None:
        now = time.time()
        while self.timestamps and now - self.timestamps[0] > 10:
            self.timestamps.popleft()
        if len(self.timestamps) >= self.max_requests:
            sleep_time = 10 - (now - self.timestamps[0])
            await asyncio.sleep(max(sleep_time, 0))
        self.timestamps.append(time.time())


# --------------------------------------------------------------------------- #
# Main client                                                                 #
# --------------------------------------------------------------------------- #
class RestPollingClient:
    """Asynchronous REST polling client."""

    TIMEFRAME_INTERVALS: Dict[str, int] = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
    }

    def __init__(
        self,
        config: Dict[str, any],
        logger: Optional[logging.Logger] = None,
        *,
        data_provider: Optional[DataProvider] = None,
        trade_planner: Optional[TradePlanner] = None,
        dispatcher: Optional[SignalDispatcher] = None,
        rate_limiter: Optional[RateLimiter] = None,
        strategy: Optional[object] = None,
    ) -> None:
        # Logger
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        # Config
        self.config = config or {}
        self.symbols = self.config.get("SYMBOLS", [])
        self.timeframes = self.config.get("TIMEFRAMES", [])

        # Components
        self.data_provider = data_provider or DataProvider()
        self.strategy      = strategy or MacdRsiStrategy()
        self.trade_planner = trade_planner or TradePlanner()
        self.dispatcher    = dispatcher or SignalDispatcher()
        self.rate_limiter  = rate_limiter or RateLimiter(max_requests_per_10s=200)

        # Metrics
        self.metrics = {
            "requests_sent": 0,
            "errors": 0,
            "latencies": [],
        }

    # ------------------------------------------------------------------ #
    # Networking                                                         #
    # ------------------------------------------------------------------ #
    async def safe_request(
        self, session: aiohttp.ClientSession, url: str
    ) -> Optional[Dict[str, any]]:
        """GET request with basic error handling & metrics."""
        try:
            start = time.time()
            async with session.get(url, timeout=10) as response:
                self.metrics["requests_sent"] += 1
                if response.status != 200:
                    raise Exception(f"Non-200 response: {response.status}")
                data = await response.json()
                self.metrics["latencies"].append(time.time() - start)
                return data
        except Exception as exc:
            self.metrics["errors"] += 1
            self.logger.warning("Request failed: %s", exc)
            await asyncio.sleep(0.5)
            return None

    # ------------------------------------------------------------------ #
    # Polling & processing                                               #
    # ------------------------------------------------------------------ #
    async def fetch_and_process(
        self, session: aiohttp.ClientSession, symbol: str, timeframe: str
    ) -> None:
        """Fetch, enrich, evaluate strategy, plan trade, dispatch."""
        await self.rate_limiter.acquire()
        url = f"https://api.lbkex.com/v2/KLine?symbol={symbol}&period={timeframe}&size=200"
        data = await self.safe_request(session, url)
        if not data:
            return

        # Raw → DataFrame
        df = self.data_provider.create_dataframe_from_kline(data)
        if df.empty:
            return

        # Indicators
        indicator = IndicatorCalculator(df.copy())
        indicator.run_all()
        enriched_df = indicator.get_df()

        # Strategy evaluation
        signal = self.strategy.generate_signal(enriched_df, symbol, timeframe)
        if not signal:
            return

        # SL/TP planning
        sltp = self.trade_planner.plan_sl_tp(symbol, signal["price"])
        signal.update(sltp)

        # Dispatch
        self.dispatcher.send_trade_signal(signal)

    async def poll_timeframe(
        self, session: aiohttp.ClientSession, tf: str
    ) -> None:
        self.logger.info("Polling timeframe %s", tf)
        tasks = [self.fetch_and_process(session, s, tf) for s in self.symbols]
        await asyncio.gather(*tasks)

    def log_metrics(self) -> None:
        import statistics

        lat = (
            statistics.mean(self.metrics["latencies"])
            if self.metrics["latencies"]
            else 0
        )
        self.logger.info(
            "📊 Requests: %s | Errors: %s | Avg latency: %.3fs",
            self.metrics["requests_sent"],
            self.metrics["errors"],
            lat,
        )

    async def polling_loop(self) -> None:
        async with aiohttp.ClientSession() as session:
            while True:
                now = int(time.time())
                for tf, interval in self.TIMEFRAME_INTERVALS.items():
                    if tf in self.timeframes and now % interval == 0:
                        await self.poll_timeframe(session, tf)
                if now % 60 == 0:
                    self.log_metrics()
                await asyncio.sleep(1)

    async def run(self) -> None:
        self.logger.info(
            "✅ RestPollingClient started – polling %d symbol(s) across %d timeframe(s)",
            len(self.symbols),
            len(self.timeframes),
        )
        try:
            await self.polling_loop()
        except asyncio.CancelledError:
            self.logger.info("Polling loop cancelled; shutting down.")

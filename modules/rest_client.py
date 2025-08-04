"""
rest_client.py
--------------
Polling client that fetches OHLCV via LBKEX REST (/v2/kline.do),
enriches with indicators, evaluates a Strategy, plans SL/TP, and
dispatches the signal.
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


# ----------------------------- constants ---------------------------------- #
SECONDS_PER_TF: Dict[str, int] = {
    "1m": 60,
    "5m": 5 * 60,
    "15m": 15 * 60,
    "30m": 30 * 60,
    "1h": 60 * 60,
    "4h": 4 * 60 * 60,
    "1d": 24 * 60 * 60,
}


# ---------------------------- rate limiter -------------------------------- #
class RateLimiter:
    """Simple sliding-window limiter (max N requests per 10 s window)."""

    def __init__(self, max_requests_per_10s: int) -> None:
        self.max_requests = max_requests_per_10s
        self.timestamps: deque[float] = deque()

    async def acquire(self) -> None:
        now = time.time()
        while self.timestamps and now - self.timestamps[0] > 10:
            self.timestamps.popleft()
        if len(self.timestamps) >= self.max_requests:
            await asyncio.sleep(10 - (now - self.timestamps[0]))
        self.timestamps.append(time.time())


# ---------------------------- polling client ------------------------------ #
class RestPollingClient:
    """Asynchronous polling client for LBKEX REST OHLCV data."""

    # when to fire per TF boundary
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
        config: Dict,
        logger: Optional[logging.Logger] = None,
        *,
        data_provider: Optional[DataProvider] = None,
        trade_planner: Optional[TradePlanner] = None,
        dispatcher: Optional[SignalDispatcher] = None,
        rate_limiter: Optional[RateLimiter] = None,
        strategy: Optional[object] = None,
    ) -> None:
        # logger
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        # config
        self.symbols = config.get("SYMBOLS", [])
        self.timeframes = config.get("TIMEFRAMES", [])
        self.rest_code_map = config.get("REST_TIMEFRAME_CODES", {})

        # components
        self.data_provider = data_provider or DataProvider()
        self.strategy = strategy or MacdRsiStrategy()
        self.trade_planner = trade_planner or TradePlanner()
        self.dispatcher = dispatcher or SignalDispatcher()
        self.rate_limiter = rate_limiter or RateLimiter(max_requests_per_10s=200)

        # metrics
        self.metrics = {
            "requests_sent": 0,
            "errors": 0,
            "latencies": [],
        }

    # -------------------------------------------------------------------- #
    async def fetch_and_process(
        self, session: aiohttp.ClientSession, symbol: str, timeframe: str
    ) -> None:
        """Fetch OHLCV, enrich, evaluate strategy, plan trade, dispatch."""
        await self.rate_limiter.acquire()

        # translate TF code to LBKEX enum, compute start timestamp
        rest_code = self.rest_code_map.get(timeframe, timeframe)
        secs_per_bar = SECONDS_PER_TF.get(timeframe)
        if secs_per_bar is None:
            self.logger.warning("Unknown timeframe %s – skipping", timeframe)
            return
        start_ts = int(time.time() - 200 * secs_per_bar)

        url = "https://api.lbkex.com/v2/kline.do"
        params = {
            "symbol": symbol,
            "type": rest_code,
            "size": 200,
            "time": start_ts,
        }

        # --- HTTP request
        try:
            t0 = time.time()
            async with session.get(url, params=params, timeout=10) as resp:
                self.metrics["requests_sent"] += 1
                if resp.status != 200:
                    raise Exception(f"HTTP {resp.status}")
                data = await resp.json()
                self.metrics["latencies"].append(time.time() - t0)
        except Exception as exc:
            self.metrics["errors"] += 1
            self.logger.warning("Request failed %s %s: %s", symbol, timeframe, exc)
            return

        # --- DataFrame + indicators
        df = self.data_provider.create_dataframe_from_kline(data)
        if df.empty:
            return
        calc = IndicatorCalculator(df.copy())
        calc.run_all()
        enriched_df = calc.get_df()

        # --- strategy
        signal = self.strategy.generate_signal(enriched_df, symbol, timeframe)
        if not signal:
            return

        # --- SL/TP planning & dispatch
        signal.update(self.trade_planner.plan_sl_tp(symbol, signal["price"]))
        self.dispatcher.send_trade_signal(signal)

    # -------------------------------------------------------------------- #
    async def poll_timeframe(self, session: aiohttp.ClientSession, tf: str):
        self.logger.info("Polling timeframe %s", tf)
        tasks = [self.fetch_and_process(session, s, tf) for s in self.symbols]
        await asyncio.gather(*tasks)

    def log_metrics(self) -> None:
        import statistics

        avg = statistics.mean(self.metrics["latencies"]) if self.metrics["latencies"] else 0
        self.logger.info(
            "📊 Requests: %s | Errors: %s | Avg latency: %.3fs",
            self.metrics["requests_sent"],
            self.metrics["errors"],
            avg,
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


    async def prefetch_all_timeframes(self) -> None:
        """
        On start-up fetch the last 200 bars for *every* symbol / timeframe
        so multi-TF features (e.g. higher-TF trend filters) are available
        immediately.
        """
        async with aiohttp.ClientSession() as session:
            for tf in self.timeframes:
                self.logger.info("📥 Prefetching %s bars for all symbols", tf)
                tasks = [
                    self.fetch_and_process(session, sym, tf)
                    for sym in self.symbols
                ]
                await asyncio.gather(*tasks)



    async def run(self) -> None:
        self.logger.info(
            "✅ RestPollingClient started – polling %s across %s",
            self.symbols,
            self.timeframes,
        )
        try:
            self.logger.info("✅ RestPollingClient starting warm-up …")
            await self.prefetch_all_timeframes()          # <── new
            self.logger.info("✅ Warm-up done, entering live loop")
            await self.polling_loop()
        except asyncio.CancelledError:
            self.logger.info("Polling loop cancelled – shutting down")


import asyncio
import time
import logging
from collections import deque
from typing import List, Dict
import aiohttp

from modules.indicator import IndicatorCalculator
from modules.strategy import TradePlanner
from modules.trader import Trader
from notifiers.SignalDispatcher import SignalDispatcher


class RateLimiter:
    def __init__(self, max_requests_per_10s: int):
        self.max_requests = max_requests_per_10s
        self.timestamps = deque()

    async def acquire(self):
        now = time.time()
        while self.timestamps and now - self.timestamps[0] > 10:
            self.timestamps.popleft()
        if len(self.timestamps) >= self.max_requests:
            sleep_time = 10 - (now - self.timestamps[0])
            await asyncio.sleep(sleep_time)
        self.timestamps.append(time.time())



import statistics
from datetime import datetime

class RestPollingClient:
    def __init_metrics(self):
        self.metrics = {
            "requests_sent": 0,
            "errors": 0,
            "latencies": [],
            "last_success": {}
        }

    def log_metrics(self):
        avg_latency = statistics.mean(self.metrics["latencies"]) if self.metrics["latencies"] else 0
        self.logger.info(f"📊 Metrics - Requests: {self.metrics['requests_sent']}, Errors: {self.metrics['errors']}, Avg Latency: {avg_latency:.2f}s")

    async def safe_request(self, session, url):
        try:
            start = time.time()
            async with session.get(url, timeout=10) as response:
                self.metrics["requests_sent"] += 1
                if response.status != 200:
                    raise Exception(f"Non-200 response: {response.status}")
                data = await response.json()
                self.metrics["latencies"].append(time.time() - start)
                return data
        except Exception as e:
            self.metrics["errors"] += 1
            self.logger.warning(f"Retrying failed request: {e}")
            await asyncio.sleep(3)
            return None

    TIMEFRAME_INTERVALS = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400
    }

    def __init__(self, config: Dict, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.config = config
        self.symbols = config["SYMBOLS"]
        self.timeframes = config["TIMEFRAMES"]
        self.rate_limiter = RateLimiter(max_requests_per_10s=200)

        self.data_provider = Trader(config, logger)
        self.indicator = IndicatorCalculator()
        self.strategy = TradePlanner(config)
        self.dispatcher = SignalDispatcher(config)
        self.__init_metrics()

    async def fetch_and_update(self, session, symbol: str, timeframe: str):
        await self.rate_limiter.acquire()
        try:
            url = f"https://api.lbkex.com/v2/KLine?symbol={symbol}&period={timeframe}&size=100"
            data = await self.safe_request(session, url)
            if data is None:
                return
                df = self.data_provider.create_dataframe_from_kline(data)
                df = self.indicator.run_all(df)
                signal = self.strategy.check_signal(df)
                if signal:
                    self.dispatcher.send_signal(signal)
        except Exception as e:
            self.logger.error(f"Error fetching {symbol}-{timeframe}: {e}")

    async def poll_timeframe(self, session, tf: str):
        self.logger.info(f"Polling timeframe: {tf}")
        tasks = [self.fetch_and_update(session, symbol, tf) for symbol in self.symbols]
        await asyncio.gather(*tasks)

    async def polling_dispatcher(self):
        async with aiohttp.ClientSession() as session:
            while True:
                now = int(time.time())
                for tf, interval in self.TIMEFRAME_INTERVALS.items():
                    if tf in self.timeframes and now % interval == 0:
                        await self.poll_timeframe(session, tf)
                self.log_metrics()
                await asyncio.sleep(1)

    async def run(self):
        self.logger.info("✅ RestPollingClient started.")
        await self.polling_dispatcher()

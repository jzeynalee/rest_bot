"""
strategy/macd_rsi.py
--------------------
Momentum / mean-reversion hybrid:

• LONG  – MACD histogram crosses ↑ through zero AND RSI < 60  
• SHORT – MACD histogram crosses ↓ through zero AND RSI > 40
"""

from __future__ import annotations
from typing import Optional, Dict
import pandas as pd

from .base import BaseStrategy


class MacdRsiStrategy(BaseStrategy):
    """MACD histogram cross filtered by RSI."""

    def generate_signal(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
    ) -> Optional[Dict]:
        # Basic safety checks
        if df is None or df.empty or len(df) < 2:
            return None

        # Ensure chronological order
        df = df.sort_values("timestamp")

        try:
            prev_hist = df["macd_hist"].iloc[-2]
            curr_hist = df["macd_hist"].iloc[-1]
            curr_rsi  = df["rsi"].iloc[-1]
            price     = df["close_price"].iloc[-1]
        except Exception:
            return None

        # Long signal
        if prev_hist < 0 < curr_hist and curr_rsi < 60:
            return {
                "symbol": symbol,
                "direction": "long",
                "price": float(price),
                "timeframe": timeframe,
            }

        # Short signal
        if prev_hist > 0 > curr_hist and curr_rsi > 40:
            return {
                "symbol": symbol,
                "direction": "short",
                "price": float(price),
                "timeframe": timeframe,
            }

        return None

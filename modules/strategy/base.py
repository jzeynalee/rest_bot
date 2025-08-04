"""
strategy/base.py
----------------
Common interface for all strategy implementations.

A Strategy receives an indicator-enriched DataFrame and decides whether
to emit a trading signal.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Dict
import pandas as pd


class BaseStrategy(ABC):
    """Abstract base strategy with a single entry point."""

    @abstractmethod
    def generate_signal(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
    ) -> Optional[Dict]:
        """
        Evaluate the enriched DataFrame and return a signal dict or None.

        Expected keys when a signal is returned
        ---------------------------------------
        symbol      : str   – trading pair (e.g. 'btc_usdt')
        direction   : str   – 'long' or 'short'
        price       : float – entry price
        timeframe   : str   – timeframe code for context
        """
        raise NotImplementedError

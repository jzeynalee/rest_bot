# rest_bot/notifiers/base.py
"""
notifiers/base.py
-----------------
A single-method interface every notifier must implement.
"""
from __future__ import annotations
from typing import Dict, List, Optional
from abc import ABC, abstractmethod

from notifiers.telegram import TelegramNotifier
from notifiers.twitter  import TwitterNotifier
from notifiers.linkedin import LinkedInNotifier

class BaseNotifier(ABC):
    """Every concrete notifier must implement send()."""

    @abstractmethod
    def send(self, text: str, image_path: Optional[str] = None) -> None:
        """Deliver message (+ optional image)."""
        raise NotImplementedError

class NotifierHub:
    def __init__(self, cfg: dict):
        self.backends: list[BaseNotifier] = []
        if cfg.get("TELEGRAM", {}).get("token"):
            self.backends.append(TelegramNotifier(**cfg["TELEGRAM"]))
        if cfg.get("TWITTER", {}).get("api_key"):
            self.backends.append(TwitterNotifier(**cfg["TWITTER"]))
        if cfg.get("LINKEDIN", {}).get("username"):
            self.backends.append(LinkedInNotifier(**cfg["LINKEDIN"]))

    def send_trade_signal(self, signal: dict, chart_path: str | None = None) -> None:
        text = self._fmt(signal)
        for b in self.backends:
            b.send(text, image_path=chart_path)

    @staticmethod
    def _fmt(s):
        return (f"📈 {s['symbol'].upper()} {s['direction'].upper()} @ {s['price']:.4f}\\n"
                f"SL {s['stop_loss']}  TP1 {s['take_profit_1']}")

# utils/image_composer.py
import matplotlib.pyplot as plt
import pandas as pd
from io import BytesIO

def compose_chart(df: pd.DataFrame, signal: dict) -> str:
    """Return path to a PNG showing last 50 candles + SL/TP lines."""
    last = df.tail(50)
    fig, ax = plt.subplots(figsize=(6,3))
    ax.plot(last["timestamp"], last["close_price"], linewidth=1)
    ax.axhline(signal["price"], color="green")
    ax.axhline(signal["stop_loss"], color="red")
    ax.axhline(signal["take_profit_1"], color="blue")
    tmp = f"/tmp/{signal['symbol']}_{signal['timeframe']}.png"
    fig.savefig(tmp, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return tmp

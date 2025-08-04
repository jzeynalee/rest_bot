# rest_bot/notifiers/base.py
"""
notifiers/base.py
-----------------
A single-method interface every notifier must implement.
"""
from __future__ import annotations
from typing import Dict, List, Optional
from abc import ABC, abstractmethod

class BaseNotifier(ABC):
    """Every concrete notifier must implement send()."""

    @abstractmethod
    def send(self, text: str, image_path: Optional[str] = None) -> None:
        """Deliver message (+ optional image)."""
        raise NotImplementedError

'''class NotifierHub:
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
                f"SL {s['stop_loss']}  TP1 {s['take_profit_1']}")'''



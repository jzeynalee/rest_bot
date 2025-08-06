"""
notifiers/hub.py
----------------
Fan-out layer that owns multiple back-end notifiers and exposes a single
`send_trade_signal()` entry point.
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional
from logging import Logger, LoggerAdapter

from notifiers.base import BaseNotifier
from notifiers.telegram import TelegramNotifier
from notifiers.twitter import TwitterNotifier
from notifiers.linkedin import LinkedInNotifier
from utils.event_bus import subscribe
from models.trade_outcome import TradeOutcome
import asyncio

class NotifierHub:
    """Collects active back-ends based on config and broadcasts messages."""

    def __init__(self, cfg: Dict) -> None:
        self.backends: List[BaseNotifier] = []

        tg_cfg = cfg.get("TELEGRAM", {})
        if tg_cfg.get("token") and tg_cfg.get("chat_id"):
            self.backends.append(
                TelegramNotifier(token=tg_cfg["token"], chat_id=tg_cfg["chat_id"])
            )

        tw_cfg = cfg.get("TWITTER", {})
        if tw_cfg.get("api_key"):
            self.backends.append(
                TwitterNotifier(
                    api_key=tw_cfg["api_key"],
                    api_secret=tw_cfg["api_secret"],
                    access_token=tw_cfg["access_token"],
                    access_secret=tw_cfg["access_secret"],
                )
            )

        li_cfg = cfg.get("LINKEDIN", {})
        if li_cfg.get("username") and li_cfg.get("password"):
            self.backends.append(
                LinkedInNotifier(username=li_cfg["username"], password=li_cfg["password"])
            )
        # notifiers/hub.py – after building each notifier
        #if backend_is_valid:
        #    self.backends.append(notifier)
        #else:
        #    logger.info("%s disabled – config missing or bad token", notifier.__class__.__name__)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def send_trade_signal(self, signal: Dict, chart_path: Optional[str] = None) -> None:
        """Format a human-readable message and fan-out to all channels."""
        text = self._format_signal(signal)
        for b in self.backends:
            try:
                b.send(text, image_path=chart_path)
            except Exception as exc:  # noqa: BLE001 (keep hub robust)
                # do NOT let one failing back-end crash the whole bot
                print(f"[NotifierHub] back-end {b.__class__.__name__} failed: {exc}")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _format_signal(s: Dict) -> str:
        """Plain-text caption; adapt to taste."""
        sym = s["symbol"].upper()
        side = s["direction"].upper()
        price = s["price"]
        tf = s["timeframe"]
        sl = s["stop_loss"]
        tp1 = s["take_profit_1"]
        return (
            f"📈 **{sym}**  ·  {side}\n"
            f"TF {tf}   Entry {price}\n"
            f"SL {sl}   TP {tp1}"
        )


    async def send_trade_outcome(self, outcome: TradeOutcome):
        txt = (
            f"✅ {outcome.symbol} TP hit @ {outcome.exit}"
            if outcome.result == "SUCCESS"
            else f"❌ {outcome.symbol} SL @ {outcome.exit}"
        )
        for backend in self.backends:
            await backend.send(txt)

# Subscribe exactly once – put this at the bottom of hub.py
subscribe(
    "trade_outcome",
    lambda o: asyncio.create_task(NotifierHub.instance().send_trade_outcome(o)),
)

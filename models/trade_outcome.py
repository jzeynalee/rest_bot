# --------------------------------------------------------------------
# models/trade_outcome.py
# One immutable record representing the *final* life‑cycle step of any signal. Dataclass shared by Trader, Portfolio, NotifierHub, etc.
# --------------------------------------------------------------------
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal


#@dataclass(frozen=True, slots=True)
@dataclass
class TradeOutcome:
    signal_id: int
    symbol: str
    side: Literal["buy", "sell"]
    entry: float
    exit: float
    closed_at: int  # epoch‑ms
    result: Literal["SUCCESS", "FAILURE"]
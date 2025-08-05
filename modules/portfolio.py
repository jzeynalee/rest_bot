"""
portfolio.py
------------
Tracks open positions and realised / unrealised PnL per symbol.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Dict, Optional


logger = logging.getLogger(__name__)


@dataclass
class Position:
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0
    realised_pnl: float = 0.0

    @property
    def is_flat(self) -> bool:  # no position open
        return abs(self.qty) < 1e-9


class PortfolioManager:
    """
    Very small in-memory portfolio for paper trading.
    A real implementation would store snapshots in SQLite on every update.
    """

    def __init__(self, persistence=None):
        self.positions: Dict[str, Position] = {}
        self.persistence = persistence

    # ------------------------------------------------------------------ #
    # Event hooks
    # ------------------------------------------------------------------ #
    def on_fill(self, symbol: str, qty: float, price: float) -> None:
        """
        Update positions on order fill (paper-trade).

        Positive qty = buy / long add, negative qty = sell / short add.
        """
        pos = self.positions.get(symbol, Position(symbol=symbol))

        # realised PnL when reducing or flipping position
        if (pos.qty > 0 > qty) or (pos.qty < 0 < qty):
            realised = qty * (pos.avg_price - price)
            pos.realised_pnl += realised

        # new weighted average
        new_qty = pos.qty + qty
        if new_qty != 0:
            pos.avg_price = (pos.avg_price * pos.qty + price * qty) / new_qty
        else:
            pos.avg_price = 0.0

        pos.qty = new_qty
        self.positions[symbol] = pos

        # persist
        if self.persistence:
            self.persistence.upsert_position(pos)

        logger.debug(
            "[Portfolio] %s qty=%f avg=%.4f realised=%.2f",
            symbol,
            pos.qty,
            pos.avg_price,
            pos.realised_pnl,
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def snapshot(self) -> Dict[str, dict]:
        """Return a dict ready for JSON / DB serialisation."""
        return {sym: asdict(pos) for sym, pos in self.positions.items()}

    def get_unrealised_pnl(self, symbol: str, last_price: float) -> float:
        pos = self.positions.get(symbol)
        if not pos or pos.is_flat:
            return 0.0
        return (last_price - pos.avg_price) * pos.qty
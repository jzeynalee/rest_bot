from __future__ import annotations
from typing import Dict, Optional, List

from utils.logger import setup_logger
from modules.sl_tp_planner import SLTPPlanner

logger = setup_logger(__name__)

class TradePlanner:
    """Coordinator for SL/TP planning and optional execution."""
    def __init__(self, data_provider=None, trader=None):
        self.data_provider = data_provider
        self.trader = trader
        
    def plan_sl_tp(
            self,
            symbol: str,
            entry_price: float,
            timeframes: Optional[list[str]] = None,
            fib_levels: Optional[dict] = None,
        ) -> Dict[str, float]:
        """
        Return a dict with stop-loss and three take-profit levels.
        Never raises if planner cannot create a valid plan.
        """
        timeframes = timeframes or ["15m", "1h", "4h"]

        # Collect higher-TF DataFrames (if a data_provider is wired)
        data_by_tf = {}
        if self.data_provider:
            for tf in timeframes:
                df = self.data_provider.get_ohlcv(symbol, tf)
                if df is not None and not df.empty:
                    data_by_tf[tf] = df
        else:
            logger.debug("plan_sl_tp(): no data_provider, proceeding with empty data.")

        planner = SLTPPlanner(
            entry_price=entry_price,
            symbol=symbol,
            data_by_timeframe=data_by_tf,
            fib_levels=fib_levels or {},
        )

        # Always call both setters; they internally guard against missing data
        planner.set_by_swing_levels()
        planner.set_by_atr()
        planner.validate_risk_reward()

        plan = planner.get_plan() or {}

        # choose first *valid* plan or fall back to default RR 1:2
        chosen = next((v for v in plan.values() if v.get("valid")), None)

        if not chosen:
            reward = entry_price * 0.02
            return {
                "stop_loss": round(entry_price - reward, 8),
                "take_profit_1": round(entry_price + reward, 8),
                "take_profit_2": round(entry_price + reward * 1.5, 8),
                "take_profit_3": round(entry_price + reward * 2.0, 8),
            }

        # Convert to flat dict expected by rest of pipeline
        sl  = float(chosen.get("sl"))
        tp1 = float(chosen.get("tp"))
        reward = tp1 - entry_price
        return {
            "stop_loss": sl,
            "take_profit_1": tp1,
            "take_profit_2": entry_price + reward * 1.5,
            "take_profit_3": entry_price + reward * 2.0,
        }

    def execute_trade(self, symbol: str, entry_price: float, sl: float, tp: float, **kwargs):
        if not self.trader:
            logger.warning("No trader injected; skipping order execution.")
            return
        self.trader.place_order(symbol=symbol, entry=entry_price, sl=sl, tp=tp, **kwargs)

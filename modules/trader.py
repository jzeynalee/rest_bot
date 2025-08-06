# modules/trader.py
import time
import hashlib
import asyncio 
import requests
import urllib.parse
from typing import Optional, Self
from utils.event_bus import publish
from ..utils.signing import hmac_sha256
from models.trade_outcome import TradeOutcome

class Trader:
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        base_url: str = "https://api.lbank.info",
        logger: Optional[object] = None,
    ):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url
        self.logger = logger
        self._base_url = base_url
        self._open: dict[str, dict] = {}  # order_id -> metadata

    def _generate_signature(self, params: dict) -> str:
        params = dict(sorted(params.items()))
        encoded = urllib.parse.urlencode(params)
        to_sign = encoded + "&secret_key=" + self.secret_key
        return hashlib.md5(to_sign.encode()).hexdigest().upper()

    def _private_post(self, endpoint: str, params: dict):
        url = self.base_url + endpoint
        params["api_key"] = self.api_key
        params["timestamp"] = int(time.time() * 1000)
        params["sign"] = self._generate_signature(params)
        resp = requests.post(url, data=params)
        data = resp.json()
        if self.logger:
            self.logger.debug("LBANK POST %s %s -> %s", endpoint, params, data)
        return data
    #####New place_order
    def place_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        *,
        price: float or None = None,
        order_style: str or None = None,  # limit, market, maker, ioc, fok
        custom_id: str or None = None,
        window: int or None = None,
        ):
        """High‑level wrapper around **/v2/supplement/create_order.do**.

        Parameters mirror LBank docs (Aug‑2025):
        https://www.lbank.com/en-US/docs/index.html#/order#place-an-order

        * ``side``      – "buy" or "sell" (case‑insensitive)
        * ``order_style`` maps to LBank ``type`` field:
              None/"limit" → ``buy`` / ``sell``
              "market"    → ``buy_market`` / ``sell_market``
              "maker"     → ``buy_maker``  / ``sell_maker``
              "ioc"       → ``buy_ioc``    / ``sell_ioc``
              "fok"       → ``buy_fok``    / ``sell_fok``
        * ``price``      – required for limit & buy_market orders
        * ``amount``     – required for limit & sell_market orders
        * ``custom_id``  – optional user‑supplied unique id
        * ``window``     – optional ms expiry window for time sync security
        """
        side = side.lower()
        style_map = {
            None: side,  # default = limit order
            "limit": side,
            "market": f"{side}_market",
            "maker": f"{side}_maker",
            "ioc": f"{side}_ioc",
            "fok": f"{side}_fok",
        }
        order_type = style_map.get(order_style, order_style)

        # -------------------- build request -------------------- #
        endpoint = "/v2/supplement/create_order.do"
        url = f"{self._base_url}{endpoint}"
        params: dict[str, str] = {
            "api_key": self._api_key,
            "symbol": symbol,
            "type": order_type,
        }
        if price is not None:
            params["price"] = str(price)
        if amount is not None:
            params["amount"] = str(amount)
        if custom_id:
            params["custom_id"] = custom_id
        if window is not None:
            params["window"] = str(window)
        # sign must be last
        params["sign"] = self._sign(params)

        resp = self._private_post(url, params)
        oid = resp.get("order_id")
        if oid:
            self._open[str(oid)] = {
                "symbol": symbol,
                "side": side,
                "entry": float(price or 0.0),
                "signal_id": resp.get("custom_id", -1),
            }
            asyncio.create_task(self._monitor_order(str(oid)))
        return resp


    # -------------------------------------------------------------- #
    async def _monitor_order(self, order_id: str, *, poll_every: int = 4) -> None:
        """Poll LBANK until the order is CLOSED/STOPPED/FILLED → emit event."""
        meta = self._open[order_id]
        symbol = meta["symbol"]
        while True:
            await asyncio.sleep(poll_every)
            info = self.get_order_info(symbol, order_id)
            status = str(info.get("status"))  # LBANK uses ints; map if needed
            if status not in {"filled", "cancelled", "partial"}:  # still live
                continue
            exit_px = float(info.get("price", 0.0) or info.get("avg_price", 0.0))
            result = (
                "SUCCESS"
                if (
                    meta["side"] == "buy" and exit_px > meta["entry"]
                )
                or (
                    meta["side"] == "sell" and exit_px < meta["entry"]
                )
                else "FAILURE"
            )
            publish(
                "trade_outcome",
                TradeOutcome(
                    signal_id=meta["signal_id"],
                    symbol=symbol,
                    side=meta["side"],
                    entry=meta["entry"],
                    exit=exit_px,
                    closed_at=int(time.time() * 1000),
                    result=result,
                ),
            )
            # tidy up & stop loop
            self._open.pop(order_id, None)
            return





    def cancel_order(self, symbol: str, order_id: str):
        return self._private_post("/v2/cancel_order.do", {"symbol": symbol, "order_id": order_id})

    def get_open_orders(self, symbol: str):
        return self._private_post("/v2/orders_info_no_deal.do", {"symbol": symbol})

    def get_order_info(self, symbol: str, order_id: str):
        return self._private_post("/v2/order_info.do", {"symbol": symbol, "order_id": order_id})

    def get_balance(self):
        return self._private_post("/v2/user_info.do", {})

# -------------------------------------------------------------------
#  🧪  tests/test_signing.py – unit tests for the signing helper and
#       for Trader.place_order() parameter assembly.
# -------------------------------------------------------------------
"""pytest‑style tests.  Run with `pytest -q tests/test_signing.py`.
Place this file in your repo at tests/test_signing.py (create the
`tests/` folder if it doesn’t exist)."""

import asyncio
import hashlib
import hmac
import pytest

from utils.signing import hmac_sha256
from modules.trader import Trader  # adjust the import path if Trader lives elsewhere


@pytest.mark.asyncio
async def test_hmac_sha256_against_manual():
    params = {
        "api_key": "testkey",
        "symbol": "lbk_usdt",
        "type": "buy_market",
        "price": "0.1",
        "amount": "10",
    }
    secret = "testsecret"

    # ---- manual reference implementation (independent) ----
    param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    md5_hex = hashlib.md5(param_str.encode()).hexdigest().upper()
    expected = hmac.new(secret.encode(), md5_hex.encode(), hashlib.sha256).hexdigest()

    assert hmac_sha256(params, secret) == expected


@pytest.mark.asyncio
async def test_trader_place_order_adds_sign(monkeypatch):
    """Intercept the private POST call so we don’t hit the real API, and
    assert that the signed param is present and non‑empty."""

    # --- patch the network layer ---
    captured: dict | None = {}

    async def fake_post(url, params):
        nonlocal captured
        captured = {"url": url, "params": params}
        return {"order_id": "dummy-id"}

    trader = Trader(api_key="A", secret_key="B")
    monkeypatch.setattr(trader, "_private_post", fake_post)

    await trader.place_order(
        symbol="lbk_usdt",
        side="buy",
        amount=10,
        price=0.1,
        order_style="market",
    )

    assert "sign" in captured["params"], "sign param missing"
    assert captured["params"]["sign"], "sign param empty"

    # LBank requires POST to /v2/supplement/create_order.do
    assert captured["url"].endswith("/v2/supplement/create_order.do")


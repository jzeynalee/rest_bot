# -------------------------------------------------------------------
#  🔐  utils/signing.py  – helper to generate the `sign` value required
#  by all authenticated LBank REST calls.
# -------------------------------------------------------------------
"""Place this file at rest_bot/utils/signing.py
   Implements the HmacSHA256 flow described in the official docs: 
   1. Alphabetically sort the parameters (excluding `sign`).
   2. Join as key=value pairs with '&'.
   3. MD5‑hash → uppercase hex.
   4. HmacSHA256(secret_key, md5_bytes) → hex digest (lower‑case)."""
from __future__ import annotations
import hashlib, hmac, random, string, time
from typing import Dict

DEFAULT_SIG_METHOD = "HmacSHA256"
__all__ = ["generate_signature", "stamp", "random_echostr"]

def stamp() -> int:
    """Server‑accepted millisecond timestamp."""
    return int(time.time() * 1000)

def random_echostr(length: int = 32) -> str:
    """Return a random alnum string (30‑40 chars) for the `echostr` param."""
    alpha = string.ascii_letters + string.digits
    if not (30 <= length <= 40):
        raise ValueError("echostr length must be 30‑40")
    return "".join(random.choice(alpha) for _ in range(length))

def generate_signature(params: Dict[str, str], secret_key: str, *, method: str = DEFAULT_SIG_METHOD) -> str:
    """Return the `sign` value to attach to `params`.

    Parameters
    ----------
    params      : dict  – all request params *excluding* `sign`.
    secret_key  : str   – your LBank secret key.
    method      : str   – currently only 'HmacSHA256' is implemented.
    """
    if "sign" in params:
        params = {k: v for k, v in params.items() if k != "sign"}
    # Step 1 & 2: alphabetical order
    ordered = "&".join(f"{k}={params[k]}" for k in sorted(params))
    # Step 3: MD5 (upper‑case hex)
    md5_hex = hashlib.md5(ordered.encode()).hexdigest().upper()
    if method.upper() == "HMACSHA256":
        # Step 4: HMAC‑SHA256 with secret key, hex digest (lower‑case)
        return hmac.new(secret_key.encode(), md5_hex.encode(), hashlib.sha256).hexdigest()
    raise NotImplementedError(f"Unsupported signature method: {method}")

# -------------------------------------------------------------------
#  ↓ Example usage inside Trader.place_order() (no changes needed in
#    the caller once this helper is imported) ↓
# -------------------------------------------------------------------
#     params = {
#         "api_key": self._api_key,
#         "symbol": symbol,
#         "type": order_type,
#         "price": maybe_fmt(price),
#         "amount": maybe_fmt(amount),
#         "custom_id": custom_id or "",
#         "window": str(window) if window else "",
#         "timestamp": str(signing.stamp()),
#         "signature_method": DEFAULT_SIG_METHOD,
#         "echostr": signing.random_echostr(),
#     }
#     params["sign"] = signing.generate_signature(params, self._secret_key)

# Docs source: LBank API "Signature Process" section citeturn7search0

# ──────────────────────────────────────────────────────────────
# Back-compat alias so older code/tests can keep using the old
# function name.  Keep this *after* generate_signature is defined.
# ──────────────────────────────────────────────────────────────
hmac_sha256 = generate_signature

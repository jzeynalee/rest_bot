"""
data_provider.py
-----------------

This module provides a simple `DataProvider` class responsible for
normalising raw kline responses from the LBank REST API into clean
Pandas DataFrames.  The API returns a JSON payload with a `data`
field containing either a list of lists (``[timestamp, open, high,
low, close, volume]``) or a list of dictionaries with named
attributes.  The `DataProvider` hides these details from the rest of
the system so callers can work with consistent column names.

If the API response is malformed or missing, an empty DataFrame is
returned to allow the caller to handle the failure gracefully.  No
exceptions are raised from within this class; the caller should
inspect the DataFrame size to determine if any rows were returned.

Example usage::

    provider = DataProvider()
    raw = await safe_request(...)  # fetch JSON from API
    df = provider.create_dataframe_from_kline(raw)
    if not df.empty:
        # do something with df

"""

from __future__ import annotations

import pandas as pd
from typing import Any, Dict, List, Optional


class DataProvider:
    """Convert raw kline JSON into a Pandas DataFrame.

    The resulting DataFrame will have the following columns with
    standardised names:

    - ``timestamp``: integer UNIX timestamp in seconds
    - ``open``: float open price
    - ``high``: float high price
    - ``low``: float low price
    - ``close``: float close price
    - ``volume``: float traded volume

    ``create_dataframe_from_kline`` silently handles unexpected
    payload structures by returning an empty DataFrame.
    """

    columns: List[str] = ["timestamp", "open", "high", "low", "close", "volume"]

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], pd.DataFrame] = {}

    def create_dataframe_from_kline(self, data: Dict[str, Any]) -> pd.DataFrame:
        """Return a DataFrame from a raw kline response.

        Parameters
        ----------
        data: Dict[str, Any]
            The decoded JSON response from the LBank API.  The
            expected shape is::

                {
                    "result": true,
                    "data": [
                        [timestamp, open, high, low, close, volume],
                        ...
                    ]
                }

            or a list of objects with the same fields.

        Returns
        -------
        pd.DataFrame
            A DataFrame with the standard columns.  An empty DataFrame
            is returned if the input does not match the expected shape.
        """
        if not isinstance(data, dict):
            return pd.DataFrame(columns=self.columns)

        raw = data.get("data")
        if raw is None:
            return pd.DataFrame(columns=self.columns)

        # If the list contains lists of length 6 we assume the order
        # matches [timestamp, open, high, low, close, volume]
        if isinstance(raw, list) and raw and isinstance(raw[0], list):
            try:
                df = pd.DataFrame(raw, columns=self.columns)
                # ensure correct dtypes
                df = df.astype({
                    "timestamp": "int64",
                    "open": "float64",
                    "high": "float64",
                    "low": "float64",
                    "close": "float64",
                    "volume": "float64",
                })
                return df
            except Exception:
                # fall through to return empty
                return pd.DataFrame(columns=self.columns)

        # If the list contains dicts, we normalise key names to the standard
        if isinstance(raw, list) and raw and isinstance(raw[0], dict):
            rows: List[Dict[str, Any]] = []
            for row in raw:
                try:
                    rows.append({
                        "timestamp": int(row.get("timestamp") or row.get("date")),
                        "open": float(row.get("open")),
                        "high": float(row.get("high")),
                        "low": float(row.get("low")),
                        "close": float(row.get("close")),
                        "volume": float(row.get("volume")),
                    })
                except Exception:
                    # skip malformed rows silently
                    continue
            return pd.DataFrame(rows, columns=self.columns)

        # unknown structure
        return pd.DataFrame(columns=self.columns)
    def put(self, symbol: str, tf: str, df: pd.DataFrame) -> None:
        """Store the most-recent DataFrame so other components can query it."""
        self._cache[(symbol, tf)] = df
        
    def get_ohlcv(self, symbol: str, tf: str) -> Optional[pd.DataFrame]:
        """Return cached DF or None if we haven’t fetched that series yet."""
        return self._cache.get((symbol, tf))
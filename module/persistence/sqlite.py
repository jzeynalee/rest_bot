"""
persistence/sqlite.py
---------------------
Simple SQLite wrapper for bars, signals, orders, positions, metrics.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS bars (
    id        INTEGER PRIMARY KEY,
    ts        INTEGER,
    symbol    TEXT,
    tf        TEXT,
    o REAL, h REAL, l REAL, c REAL, v REAL
);

CREATE TABLE IF NOT EXISTS signals (
    id        INTEGER PRIMARY KEY,
    ts        INTEGER,
    symbol    TEXT,
    tf        TEXT,
    direction TEXT,
    price     REAL,
    payload   TEXT          -- raw JSON blob
);

CREATE TABLE IF NOT EXISTS positions (
    symbol       TEXT PRIMARY KEY,
    qty          REAL,
    avg_price    REAL,
    realised_pnl REAL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    ts INTEGER,
    symbol TEXT,
    side TEXT,
    qty REAL,
    price REAL,
    status TEXT
);

CREATE TABLE IF NOT EXISTS metrics (
    name TEXT,
    ts   INTEGER,
    value REAL,
    PRIMARY KEY (name, ts)
);
"""


class SQLitePersistence:
    def __init__(self, db_path: str = "restbot.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ---------------------------- INSERTS -------------------------------- #
    def insert_signal(self, signal: Dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO signals (ts, symbol, tf, direction, price, payload)
            VALUES (:ts, :symbol, :tf, :direction, :price, :payload)
            """,
            {
                "ts": signal.get("timestamp") or signal.get("ts") or 0,
                "symbol": signal["symbol"],
                "tf": signal["timeframe"],
                "direction": signal["direction"],
                "price": signal["price"],
                "payload": json.dumps(signal),
            },
        )
        self.conn.commit()

    def upsert_position(self, pos) -> None:
        self.conn.execute(
            """
            INSERT INTO positions (symbol, qty, avg_price, realised_pnl)
            VALUES (:symbol, :qty, :avg_price, :realised)
            ON CONFLICT(symbol) DO UPDATE SET
              qty = excluded.qty,
              avg_price = excluded.avg_price,
              realised_pnl = excluded.realised_pnl
            """,
            {
                "symbol": pos.symbol,
                "qty": pos.qty,
                "avg_price": pos.avg_price,
                "realised": pos.realised_pnl,
            },
        )
        self.conn.commit()

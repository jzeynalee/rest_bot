"""
utils/image_composer.py
-----------------------
Creates a small PNG with the last ~50 closing prices + SL/TP lines so
Telegram/X posts look more engaging.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt
import pandas as pd

def compose_chart(df: pd.DataFrame, signal: Dict, save_dir: str = "/tmp") -> str:
    """
    Draw a mini chart and return the file path.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain `timestamp` and `close_price`.
    signal : dict
        Must contain `price`, `stop_loss`, `take_profit_1`, `symbol`, `timeframe`.
    save_dir : str
        Directory to write the PNG (default /tmp).

    Returns
    -------
    str
        Path to the saved PNG file.
    """
    last = df.tail(50)

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(last["timestamp"], last["close_price"], linewidth=1.3, label="Price")

    # horizontal lines
    ax.axhline(signal["price"], color="lime",  linewidth=0.8, label="Entry")
    ax.axhline(signal["stop_loss"], color="red", linewidth=0.8, label="SL")
    ax.axhline(signal["take_profit_1"], color="blue", linewidth=0.8, label="TP1")

    ax.set_title(f"{signal['symbol'].upper()} – {signal['timeframe']}")
    ax.set_xlabel("Time")
    ax.set_ylabel("Price")
    ax.legend(loc="upper left", fontsize=8)
    plt.tight_layout()

    # save to disk
    out_path = Path(save_dir) / f"{signal['symbol']}_{signal['timeframe']}.png"
    fig.savefig(out_path, dpi=120)
    plt.close(fig)

    return str(out_path)

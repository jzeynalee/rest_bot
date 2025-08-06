# REST-API Trading Bot (MVP Plus 2025)

Minimal yet extensible trading bot for the **LBKEX** cryptocurrency
exchange – now refactored for cleaner architecture, multi-time-frame
analysis, portfolio tracking and SQLite persistence.

<p align="center">
  <img src="docs/img/signal_card_example.png" width="550"
       alt="Sample Telegram/X signal card">
</p>

---

## Features (2025 Refactor)

| Layer            | Highlights                                                     |
| ---------------- | -------------------------------------------------------------- |
| **Data ingestion** | Scheduled REST polling (`RestFetcher`) + warm-up of all TFs. |
| **Indicators**     | `IndicatorCalculator` (Ichimoku, Keltner, Bollinger, RSI, MACD, …). |
| **Strategy**       | Plug-and-play (`StrategyEngine`) – default MACD hist × RSI. |
| **Risk / SL-TP**   | `TradePlanner` + `SLTPPlanner` with ATR & swing-high filters. |
| **Portfolio**      | `PortfolioManager` tracks qty, WAP, realised/unrealised PnL. |
| **Execution**      | `Trader` (paper-trade or real keys).                         |
| **Notifications**  | `NotifierHub` (Telegram, X, LinkedIn) with auto-generated image cards. |
| **Persistence**    | SQLite v1 schema – bars, signals, orders, positions, metrics. |
| **Analytics**      | CLI snapshots; Prometheus exporter (beta).                   |
| **Testing**        | Pytest fixtures + vectorised back-tester.                    |

---

## Directory Tree (simplified)

Below is a drop-in replacement for your project’s top-level README.md.  It keeps the quick-start you already had, but adds the new modules (Portfolio & Persistence, Notifier Hub with image cards, multi-TF warm-up, etc.), refreshed directory tree, and instructions for running tests and the back-tester.

Copy-paste this over the current README.md in jzeynalee/rest_bot and commit.

# REST-API Trading Bot (MVP Plus 2025)

Minimal yet extensible trading bot for the **LBKEX** cryptocurrency
exchange – now refactored for cleaner architecture, multi-time-frame
analysis, portfolio tracking and SQLite persistence.

<p align="center">
  <img src="docs/img/signal_card_example.png" width="550"
       alt="Sample Telegram/X signal card">
</p>

---

## Features (2025 Refactor)

| Layer            | Highlights                                                     |
| ---------------- | -------------------------------------------------------------- |
| **Data ingestion** | Scheduled REST polling (`RestFetcher`) + warm-up of all TFs. |
| **Indicators**     | `IndicatorCalculator` (Ichimoku, Keltner, Bollinger, RSI, MACD, …). |
| **Strategy**       | Plug-and-play (`StrategyEngine`) – default MACD hist × RSI. |
| **Risk / SL-TP**   | `TradePlanner` + `SLTPPlanner` with ATR & swing-high filters. |
| **Portfolio**      | `PortfolioManager` tracks qty, WAP, realised/unrealised PnL. |
| **Execution**      | `Trader` (paper-trade or real keys).                         |
| **Notifications**  | `NotifierHub` (Telegram, X, LinkedIn) with auto-generated image cards. |
| **Persistence**    | SQLite v1 schema – bars, signals, orders, positions, metrics. |
| **Analytics**      | CLI snapshots; Prometheus exporter (beta).                   |
| **Testing**        | Pytest fixtures + vectorised back-tester.                    |

---

## Directory Tree (simplified)

rest_bot/ ├─ main.py                    ← CLI entry ├─ config.env.example ├─ modules/ │  ├─ rest_fetcher.py         ← REST polling │  ├─ strategy_engine.py │  ├─ indicator.py │  ├─ trade_planner.py │  ├─ sl_tp_planner.py │  ├─ portfolio.py │  └─ persistence/ │     └─ sqlite.py ├─ notifiers/ │  ├─ hub.py                  ← fan-out │  ├─ base.py │  ├─ telegram.py │  ├─ twitter.py │  └─ linkedin.py └─ utils/ └─ image_composer.py

*(Legacy files like `modules/rest_client.py` remain for backward
compatibility but delegate to the new components.)*

---

## Quick Start

```bash
# 1  clone repo & create virtualenv
git clone https://github.com/jzeynalee/rest_bot.git
cd rest_bot
python -m venv .venv && source .venv/bin/activate

# 2  install deps
pip install -r requirements.txt

# 3  copy config and edit symbols / time-frames / API keys
cp config.env.example config.env   # edit in your editor

# 4  run (paper-trade)
python rest_bot/main.py

Signals will print to stdout and—if tokens are set—will be posted to Telegram / X / LinkedIn with a mini chart.


---

Configuration (config.env)

# Symbols & TFs
SYMBOLS=btc_usdt,eth_usdt
TIMEFRAMES=1m,5m,15m

# LBKEX REST code map
REST_TIMEFRAME_CODES_1M=minute1
REST_TIMEFRAME_CODES_5M=minute5
# …

# Telegram (optional)
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=

# Twitter / X (optional)
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_SECRET=

Leave a section blank to disable that notifier.


---

Persistence & Analytics

SQLite file restbot.db is created automatically.

Example query:


sqlite3 restbot.db '
SELECT date(ts, "unixepoch") day,
       COUNT(*) signals,
       SUM(json_extract(payload, "$.direction"=="long")) longs
FROM signals
GROUP BY day;'

Prometheus exporter under utils/prom_exporter.py (run separately).



---

Testing & Back-testing

# unit tests
pytest -q

# run vectorised back-test
python tests/backtest_runner.py --symbols btc_usdt --tf 1m --csv data/btc_1m_2024.csv

Back-test outputs equity curve + Sharpe to reports/.


---

Roadmap (Q3 2025)

1. Live order router with smart-price ladder.


2. VaR limits & circuit-breakers in RiskEngine.


3. Prometheus dashboards for hit-rate, latency and PnL.


4. Docker image & Helm chart.


5. Optional Rust micro-service for ultra-low-latency indicators.




---

License

MIT © 2025 Javad Zeynali

---

### How to commit

```bash
# in your cloned repo
echo "<paste the content above>" > README.md
git add README.md
git commit -m "docs: refresh README for MVP-Plus refactor (Aug 2025)"
git push origin main

Feel free to tweak wording or add screenshots—this README should now match the refactored architecture and new modules we just added.


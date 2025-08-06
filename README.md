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

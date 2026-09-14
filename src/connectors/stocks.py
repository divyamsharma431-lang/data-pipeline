"""
Stocks / crypto connector -- yfinance (Yahoo Finance)

No API key required. Works for stock tickers (AAPL, MSFT) and crypto
pairs (BTC-USD, ETH-USD) using the same interface.
"""

import yfinance as yf

from .base import BaseConnector


class StocksConnector(BaseConnector):
    source_name = "stocks"

    def __init__(self, tickers: list[str]):
        self.tickers = tickers

    def fetch(self) -> dict:
        results = {}
        for ticker in self.tickers:
            t = yf.Ticker(ticker)
            info = t.fast_info
            results[ticker] = {
                "last_price": info.get("last_price"),
                "previous_close": info.get("previous_close"),
                "day_high": info.get("day_high"),
                "day_low": info.get("day_low"),
            }
        return results

    def transform(self, raw: dict) -> list[dict]:
        rows = []
        ts = self.now_iso()
        for ticker, info in raw.items():
            for metric, value in info.items():
                if value is not None:
                    rows.append({
                        "source": self.source_name,
                        "timestamp": ts,
                        "metric": metric,
                        "value": float(value),
                        "label": ticker,
                        "metadata": {},
                    })
        return rows

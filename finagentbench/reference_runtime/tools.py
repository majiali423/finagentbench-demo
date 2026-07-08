from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .cache import MemoryCache


@dataclass(frozen=True)
class ToolEvent:
    tool: str
    entity: str
    status: str
    attempts: int
    cached: bool = False
    error: str = ""


FINANCIALS = {
    "AAPL": {"revenue": 382.7, "free_cash_flow": 99.6, "period": "FY2025"},
    "MSFT": {"revenue": 240.0, "free_cash_flow": 73.28, "period": "FY2025"},
    "NVDA": {"revenue": 130.48, "free_cash_flow": 67.77, "period": "FY2025"},
}


MARKET_DATA = {
    "AAPL": {"status": "ok", "provider": "demo-market-api", "as_of": "2026-07-08"},
    "MSFT": {"status": "ok", "provider": "demo-market-api", "as_of": "2026-07-08"},
    "NVDA": {"status": "ok", "provider": "demo-market-api", "as_of": "2026-07-08"},
}


class FinancialStatementTool:
    name = "financial_statement"

    def __init__(self, cache: MemoryCache) -> None:
        self.cache = cache
        self.events: list[ToolEvent] = []

    def fetch(self, symbol: str) -> dict[str, Any]:
        cache_key = f"financials:{symbol}"
        was_cached = cache_key in self.cache._items

        def load() -> dict[str, Any]:
            if symbol not in FINANCIALS:
                raise KeyError(f"No financial statement data for {symbol}")
            return dict(FINANCIALS[symbol])

        result = self.cache.get_or_set(cache_key, load)
        self.events.append(ToolEvent(self.name, symbol, "ok", attempts=1, cached=was_cached))
        return dict(result)


class MarketDataTool:
    name = "market_data"

    def __init__(self, cache: MemoryCache, transient_failures: dict[str, int] | None = None) -> None:
        self.cache = cache
        self.remaining_failures = dict(transient_failures or {})
        self.events: list[ToolEvent] = []

    def fetch_with_retry(self, symbol: str, max_attempts: int = 2) -> dict[str, Any]:
        cache_key = f"market:{symbol}"
        was_cached = cache_key in self.cache._items
        attempts = 0
        last_error = ""

        def load() -> dict[str, Any]:
            nonlocal attempts, last_error
            for attempt in range(1, max_attempts + 1):
                attempts = attempt
                if self.remaining_failures.get(symbol, 0) > 0:
                    self.remaining_failures[symbol] -= 1
                    last_error = "rate_limit"
                    continue
                if symbol not in MARKET_DATA:
                    last_error = "not_found"
                    break
                return {"entity": symbol, **MARKET_DATA[symbol]}
            return {
                "entity": symbol,
                "status": "failed",
                "provider": "demo-market-api",
                "as_of": "2026-07-08",
                "error": last_error or "unknown",
            }

        result = self.cache.get_or_set(cache_key, load)
        status = str(result.get("status", "ok"))
        self.events.append(
            ToolEvent(self.name, symbol, status, attempts=max(1, attempts), cached=was_cached, error=last_error)
        )
        return dict(result)

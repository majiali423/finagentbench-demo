from __future__ import annotations

from dataclasses import dataclass

from .cache import MemoryCache


@dataclass(frozen=True)
class RetrievedDoc:
    entity: str
    citation: str
    period: str
    source_type: str
    provider: str
    text: str


DOCS = {
    "AAPL": RetrievedDoc(
        "AAPL",
        "aapl_10k_2025.pdf#cashflow",
        "FY2025",
        "annual_report",
        "company_filing",
        "Revenue and free cash flow values from annual filing evidence.",
    ),
    "MSFT": RetrievedDoc(
        "MSFT",
        "msft_10k_2025.pdf#financials",
        "FY2025",
        "annual_report",
        "company_filing",
        "Revenue and free cash flow values from annual filing evidence.",
    ),
    "NVDA": RetrievedDoc(
        "NVDA",
        "nvda_10k_2025.pdf#liquidity",
        "FY2025",
        "annual_report",
        "company_filing",
        "Revenue and free cash flow values from annual filing evidence.",
    ),
}


class InMemoryRetriever:
    def __init__(self, cache: MemoryCache) -> None:
        self.cache = cache

    def search(self, symbol: str) -> RetrievedDoc:
        cache_key = f"retrieval:{symbol}"
        return self.cache.get_or_set(cache_key, lambda: DOCS[symbol])

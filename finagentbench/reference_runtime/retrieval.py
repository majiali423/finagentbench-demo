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
        "AAPL free cash flow was 99.6 billion USD and revenue was 382.7 billion USD for FY2025.",
    ),
    "MSFT": RetrievedDoc(
        "MSFT",
        "msft_10k_2025.pdf#financials",
        "FY2025",
        "annual_report",
        "company_filing",
        "MSFT free cash flow was 73.28 billion USD and revenue was 240.0 billion USD for FY2025.",
    ),
    "NVDA": RetrievedDoc(
        "NVDA",
        "nvda_10k_2025.pdf#liquidity",
        "FY2025",
        "annual_report",
        "company_filing",
        "NVDA free cash flow was 67.77 billion USD and revenue was 130.48 billion USD for FY2025.",
    ),
}


class InMemoryRetriever:
    def __init__(self, cache: MemoryCache) -> None:
        self.cache = cache

    def search(self, symbol: str) -> RetrievedDoc:
        cache_key = f"retrieval:{symbol}"
        return self.cache.get_or_set(cache_key, lambda: DOCS[symbol])

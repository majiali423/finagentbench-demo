from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .cache import MemoryCache
from .retrieval import InMemoryRetriever
from .tools import FinancialStatementTool, MarketDataTool


def run_reference_agent(query: str | None = None) -> dict[str, Any]:
    symbols = ["AAPL", "MSFT", "NVDA"]
    cache = MemoryCache()
    retriever = InMemoryRetriever(cache)
    financials_tool = FinancialStatementTool(cache)
    market_tool = MarketDataTool(cache, transient_failures={"NVDA": 1})

    steps = [{"name": "planning", "status": "ok"}]

    evidence = []
    for symbol in symbols:
        doc = retriever.search(symbol)
        evidence.append(asdict(doc))
    steps.append({"name": "retrieval", "status": "ok"})

    metrics = []
    for symbol in symbols:
        data = financials_tool.fetch(symbol)
        period = str(data["period"])
        metrics.append(
            {
                "entity": symbol,
                "name": "free_cash_flow_margin",
                "period": period,
                "value": round(data["free_cash_flow"] / data["revenue"], 6),
                "formula": "free_cash_flow / revenue",
                "inputs": {
                    "free_cash_flow": {
                        "value": data["free_cash_flow"],
                        "unit": "billion",
                        "currency": "USD",
                        "period": period,
                    },
                    "revenue": {
                        "value": data["revenue"],
                        "unit": "billion",
                        "currency": "USD",
                        "period": period,
                    },
                },
            }
        )
    steps.append({"name": "quant", "status": "ok"})

    market_data = [market_tool.fetch_with_retry(symbol) for symbol in symbols]
    steps.append({"name": "risk", "status": "ok"})

    winner = max(metrics, key=lambda item: float(item["value"]))
    steps.append({"name": "synthesis", "status": "ok"})
    steps.append({"name": "compliance", "status": "ok"})

    final_output = (
        "AAPL, MSFT, and NVDA were compared using cited annual filing evidence. "
        f"{winner['entity']} has the highest free cash flow margin in this run. "
        "The analysis includes valuation risk and data limitations, including a transient "
        "market-data retry for NVDA. This is research output only and not investment advice."
    )

    return {
        "run_id": "reference-agent-bigtech-fcf",
        "query": query or "Compare AAPL, MSFT, and NVDA free cash flow margin and valuation risk.",
        "metadata": {
            "runtime": "reference_runtime",
            "orchestration": "plan-retrieve-quant-risk-synthesize-compliance",
            "cache": cache.stats(),
            "tool_events": [asdict(event) for event in financials_tool.events + market_tool.events],
        },
        "entities": [{"name": symbol, "symbol": symbol} for symbol in symbols],
        "steps": steps,
        "metrics": metrics,
        "evidence": evidence,
        "market_data": market_data,
        "final_output": final_output,
    }

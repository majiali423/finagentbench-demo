from __future__ import annotations

import re
from typing import Any


def input_value(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("value")
    return value


def input_period(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("period") or "")
    return ""


def input_unit(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("unit") or "")
    return ""


def input_currency(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("currency") or "")
    return ""


def extract_numbers(text: str) -> list[float]:
    values = []
    for match in re.finditer(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?", text):
        raw = match.group(0).replace(",", "")
        try:
            values.append(float(raw))
        except ValueError:
            continue
    return values

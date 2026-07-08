from __future__ import annotations

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

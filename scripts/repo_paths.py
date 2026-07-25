"""Portable repository discovery for cross-project validation scripts."""

from __future__ import annotations

import os
from pathlib import Path


def finagentbench_root() -> Path:
    return Path(__file__).resolve().parents[1]


def lumenfin_root() -> Path:
    configured = os.getenv("LUMENFIN_ROOT")
    candidates = [
        Path(configured).expanduser() if configured else None,
        finagentbench_root().parent / "lumenfin-agent",
    ]
    for candidate in candidates:
        if candidate and (candidate / "src" / "lumenfin").is_dir():
            return candidate.resolve()
    raise RuntimeError(
        "LumenFin repository not found. Set LUMENFIN_ROOT or clone "
        "lumenfin-agent next to finagentbench-demo."
    )

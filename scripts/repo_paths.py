"""Portable repository discovery for cross-project validation scripts."""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any


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


def load_lumenfin_export_finrun_state() -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Load ``export_finrun_state`` without importing ``lumenfin.__init__``.

    LumenFin's package root constructs the FastAPI app at import time and may
    require database configuration. Offline FinRun export only needs
    ``finrun.py`` and ``metrics_schema.py``.
    """

    lumen = lumenfin_root()
    pkg_dir = lumen / "src" / "lumenfin"
    src_root = lumen / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))

    existing = sys.modules.get("lumenfin")
    if existing is not None and hasattr(existing, "create_app"):
        from lumenfin.finrun import export_finrun_state

        return export_finrun_state

    if "lumenfin" not in sys.modules:
        pkg = types.ModuleType("lumenfin")
        pkg.__path__ = [str(pkg_dir)]
        pkg.__file__ = str(pkg_dir / "__init__.py")
        sys.modules["lumenfin"] = pkg

    def _load(module_name: str, path: Path):
        if module_name in sys.modules and getattr(sys.modules[module_name], "__file__", None):
            return sys.modules[module_name]
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load {module_name} from {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    _load("lumenfin.metrics_schema", pkg_dir / "metrics_schema.py")
    finrun = _load("lumenfin.finrun", pkg_dir / "finrun.py")
    export = getattr(finrun, "export_finrun_state", None)
    if not callable(export):
        raise RuntimeError("lumenfin.finrun.export_finrun_state is unavailable")
    return export

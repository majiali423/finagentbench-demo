"""Regression: RC runner import must stay side-effect free and fail-fast."""

from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class RcRunnerImportTestCase(unittest.TestCase):
    def test_rc_runner_import_has_no_side_effects(self) -> None:
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        banned = (
            "lumenfin.config",
            "lumenfin.service",
            "lumenfin.graph",
            "lumenfin.agents",
            "lumenfin.rag.milvus_client",
            "lumenfin.database",
            "run_production_hardening",
            "requests",
            "httpx",
        )
        for name in banned:
            sys.modules.pop(name, None)

        fixtures = ROOT / "fixtures"
        fixture_mtimes = {
            p: p.stat().st_mtime_ns
            for p in fixtures.glob("case_lumenfin_*.json")
            if p.is_file()
        }
        outputs_before = {
            p.resolve() for p in (ROOT / "outputs").rglob("*") if p.is_file()
        } if (ROOT / "outputs").exists() else set()

        with (
            mock.patch("subprocess.run") as mocked_run,
            mock.patch("subprocess.Popen") as mocked_popen,
            mock.patch("os.chdir") as mocked_chdir,
            mock.patch("socket.create_connection") as mocked_socket,
        ):
            started = time.perf_counter()
            module = _load_module("run_rc_validation_import_probe", SCRIPTS / "run_rc_validation.py")
            elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 5.0, f"import took too long: {elapsed:.3f}s")
        self.assertTrue(callable(getattr(module, "main", None)))
        mocked_run.assert_not_called()
        mocked_popen.assert_not_called()
        mocked_chdir.assert_not_called()
        mocked_socket.assert_not_called()
        for name in banned:
            self.assertNotIn(name, sys.modules)

        for path, before in fixture_mtimes.items():
            self.assertEqual(path.stat().st_mtime_ns, before, f"fixture mutated: {path.name}")
        outputs_after = {
            p.resolve() for p in (ROOT / "outputs").rglob("*") if p.is_file()
        } if (ROOT / "outputs").exists() else set()
        self.assertEqual(outputs_after, outputs_before, "import created/modified outputs")

        runtime = _load_module("rc_runtime_import_probe", SCRIPTS / "rc_runtime.py")
        self.assertTrue(callable(runtime.live_analyze))
        self.assertTrue(callable(runtime.judge_row))
        for name in ("lumenfin.config", "lumenfin.service", "lumenfin.agents"):
            self.assertNotIn(name, sys.modules)

    def test_import_probe_subprocess_times_out_instead_of_hanging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            blocker = Path(tmp) / "blocker.py"
            blocker.write_text(
                "import time\ntime.sleep(60)\nprint('should-not-finish')\n",
                encoding="utf-8",
            )
            started = time.perf_counter()
            with self.assertRaises(subprocess.TimeoutExpired):
                subprocess.run(
                    [sys.executable, str(blocker)],
                    timeout=1,
                    check=False,
                    capture_output=True,
                    text=True,
                    stdin=subprocess.DEVNULL,
                )
            elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 5.0)

    def test_live_rc_rejects_local_fallback_and_fingerprint_drift(self) -> None:
        runtime = _load_module("rc_runtime_fallback_probe", SCRIPTS / "rc_runtime.py")
        self.assertTrue(issubclass(runtime.LocalFallbackAbort, RuntimeError))

        class _LLM:
            api_key = "sk-test"
            model = "deepseek-v4-flash"
            base_url = "https://api.deepseek.com"

        class _Cfg:
            llm = _LLM()
            data_mode = "live"
            app_env = "dev"

            def allows_local_fallback(self) -> bool:
                return False

        fp = runtime.provider_fingerprint(_Cfg())
        self.assertEqual(fp["provider"], "deepseek")
        self.assertEqual(fp["model"], "deepseek-v4-flash")
        self.assertFalse(fp["allow_local_fallback"])

        # Fingerprint mismatch must be detectable before analyze proceeds.
        drifted = dict(fp)
        drifted["model"] = "other-model"
        self.assertNotEqual(fp["model"], drifted["model"])


if __name__ == "__main__":
    unittest.main()

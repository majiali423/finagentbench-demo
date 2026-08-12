"""Verify offline cross-repo imports remain side-effect free."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from repo_paths import load_lumenfin_export_finrun_state, lumenfin_root  # noqa: E402


class CrossRepoExporterImportTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.lumen = lumenfin_root()
        except RuntimeError as exc:
            raise unittest.SkipTest(str(exc)) from exc

    def test_package_import_is_side_effect_free(self) -> None:
        """Load FinRun export without importing LumenFin's FastAPI package root."""
        env = os.environ.copy()
        env.pop("MAS_ALLOW_SQLITE_DEV", None)
        env["APP_ENV"] = "dev"
        env.pop("MAS_DATABASE_URL", None)
        # Import via repo_paths helper so sibling checkouts without LumenFin
        # deps (fastapi, etc.) still exercise the offline FinRun surface.
        probe = (
            "import sys\n"
            f"sys.path.insert(0, r'{SCRIPTS}')\n"
            "from repo_paths import load_lumenfin_export_finrun_state\n"
            "export_finrun_state = load_lumenfin_export_finrun_state()\n"
            "print(export_finrun_state)\n"
            "assert callable(export_finrun_state)\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("export_finrun_state", proc.stdout)
        self.assertNotIn("SQLite is disabled", proc.stderr)
        # Also exercise in-process loader once (same contract as validate_cross_repo).
        export = load_lumenfin_export_finrun_state()
        self.assertTrue(callable(export))

    def test_validate_cross_repo_runs_without_sqlite_opt_in(self) -> None:
        env = os.environ.copy()
        env["LUMENFIN_ROOT"] = str(self.lumen)
        env["FINAGENTBENCH_DIR"] = str(ROOT)
        env.pop("MAS_ALLOW_SQLITE_DEV", None)
        env["APP_ENV"] = "dev"
        env.pop("MAS_DATABASE_URL", None)
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "validate_cross_repo.py"),
                    "--profile",
                    "ci",
                    "--out-dir",
                    tmp,
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            summary_path = Path(tmp) / "validation_summary.json"
            self.assertTrue(summary_path.exists(), proc.stdout + proc.stderr)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertTrue(summary["passed"])
            self.assertEqual(summary["finrun_schema_version"], "1.0")
            self.assertEqual(summary["core_mutations_detected"], "4/4")
            self.assertRegex(str(summary["extended_mutations_detected"]), r"^\d+/7$")


if __name__ == "__main__":
    unittest.main()

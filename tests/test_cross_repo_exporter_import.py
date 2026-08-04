"""Expose package-init side effects that break offline cross-repo validation."""

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

from repo_paths import lumenfin_root  # noqa: E402


class CrossRepoExporterImportTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.lumen = lumenfin_root()
        except RuntimeError as exc:
            raise unittest.SkipTest(str(exc)) from exc

    def test_package_import_triggers_app_side_effects(self) -> None:
        """Document why validate_cross_repo must not import the LumenFin package root."""
        env = os.environ.copy()
        env.pop("MAS_ALLOW_SQLITE_DEV", None)
        env["APP_ENV"] = "dev"
        env.pop("MAS_DATABASE_URL", None)
        probe = (
            "import sys\n"
            f"sys.path.insert(0, r'{self.lumen / 'src'}')\n"
            "from lumenfin.finrun import export_finrun_state\n"
            "print(export_finrun_state)\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertNotEqual(
            proc.returncode,
            0,
            "Expected LumenFin package import to fail closed without DB opt-in; "
            "if this starts passing, revisit the side-effect-free loader assumption.",
        )
        self.assertIn("SQLite is disabled", proc.stderr)

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

# FinAgentBench portfolio pack

Thin entry for recruiters and clean-clone reviewers. Interview/private notes
do not belong in this repository.

## Start here

| Step | Command / doc |
|------|----------------|
| 1. Offline demo | `python scripts/run_offline_demo.py` |
| 2. Why this repo exists | [README — Why a separate evaluator repository?](../README.md#why-a-separate-evaluator-repository) |
| 3. Release evidence | [../reports/current/FinAgentBench_Final_Release_Report.md](../reports/current/FinAgentBench_Final_Release_Report.md) |
| 4. Validation menu | [VALIDATION_COMMANDS.md](VALIDATION_COMMANDS.md) |
| 5. CI lanes | [CI_GATE.md](CI_GATE.md) |

## Reproducibility (short)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -e .
python scripts/run_offline_demo.py
# optional
python -m unittest discover -s tests -v
python scripts/run_mutation_suite.py
```

No API keys. Sibling LumenFin is optional for the offline demo; required only
for cross-repo producer checks (`LUMENFIN_ROOT` or `../lumenfin-agent`).

**Pins (do not conflate):**

| Direction | Pin |
|-----------|-----|
| This package (`v0.1.0-rc.4`) → LumenFin producer | `v0.1.0-rc.3` |
| LumenFin CI → this evaluator | still `v0.1.0-rc.3` |

## Limitations (short)

- Replay-first reliability gate — **not** an investment-quality proof
- Deterministic metrics are the release path; semantic judge is optional
- Passing does not certify the Agent for production trading or fiduciary use
- Cross-repo import uses `scripts/repo_paths.load_lumenfin_export_finrun_state`
  so a sibling LumenFin tree does not require FastAPI in this venv

Fuller product limitations for the Agent side live in LumenFin
`docs/PRODUCTION_LIMITATIONS.md`.

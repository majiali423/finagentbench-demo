# CI Gate

FinAgentBench `0.1.0rc4` provides a replay-first, offline release gate.

## Default workflow

The GitHub workflow runs on `push` and `pull_request` with no secrets and no
live providers.

Both Python lanes require the known-fail fixture to exit with status `1` and
produce a fresh evaluation report with the expected run ID and `passed=false`.
A CLI crash, missing report or unexpected success fails CI; a nonzero exit
alone is not proof of a valid negative-control rejection.

Matrix:

| Python | Suite |
|--------|-------|
| 3.11 | unit tests + CLI/schema smoke + known-fail block |
| 3.12 | full unit + benchmark + mutation + static semantic replay + pinned LumenFin cross-repo |

Full suite includes:

1. Unit tests
2. Deterministic fixture gates
3. Due-diligence and LumenFin regression suites
4. Core + extended reliability mutation gate
5. Static semantic replay suites (no network)
6. Expected-failure blocking assertion
7. Reference runtime export/evaluation
8. Required pinned cross-repo gate on the Python 3.12 full lane:
   `majiali423/lumenfin-agent@v0.1.0-rc.3`

Generated `outputs/` reports are uploaded as CI artifacts.

The [2026-09-09 source baseline](https://github.com/majiali423/finagentbench-demo/actions/runs/34329922587)
passed at `40f7599`. LumenFin's separate
[Product quality v3 job](https://github.com/majiali423/lumenfin-agent/actions/runs/34329999879)
installs that evaluator commit via `FINAGENTBENCH_PRODUCT_REF` and runs the
product workflow tests. Frozen rc.3/rc.4 evaluator jobs cover compatibility;
they do not replace that v3 job.

## Cross-repository gate

```bash
python scripts/validate_cross_repo.py --profile ci
```

The summary records:

- LumenFin commit and tag pin
- FinAgentBench commit
- FinRun schema version
- benchmark profile
- core mutation result
- extended mutation result
- final pass/fail

The command prints evaluator diagnostics and writes
`outputs/cross_repo_validation/validation_summary.json`.

## Profiles

- `ci`: deterministic metrics only; release blocking.
- `audit`: adds semantic metrics and requires a configured/static judge.
- `default`: case as authored.

Live semantic judges and live LumenFin RC runs are manual/nightly activities,
not ordinary PR requirements.

## Failure interpretation

- Formula/entity/evidence findings are Agent/export contract failures.
- Missing repository, unsupported schema or fixture mismatch are release
  configuration failures.
- Live API quota/network/model failure is infrastructure failure.

All are non-pass, but reports must preserve the category for diagnosis.

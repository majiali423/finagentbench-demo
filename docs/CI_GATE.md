# CI Gate

FinAgentBench `0.1.0rc1` provides a replay-first, offline release gate.

## Default workflow

The GitHub workflow runs:

1. Unit tests
2. Deterministic fixture gates
3. Due-diligence and LumenFin regression suites
4. Four-mutation reliability gate
5. Static semantic replay suites
6. Expected-failure blocking assertion
7. Reference runtime export/evaluation

Generated `outputs/` reports are uploaded as CI artifacts.

## Cross-repository gate

```bash
python scripts/validate_cross_repo.py --profile ci
```

The summary records:

- LumenFin commit
- FinAgentBench commit
- FinRun schema version
- benchmark profile
- mutation detection rate/results
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

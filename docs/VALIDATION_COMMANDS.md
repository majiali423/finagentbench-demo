# FinAgentBench Validation Commands

Supported release entrypoints only. Historical scripts under
`tools/archived_audits/` are unsupported and are not gates.

## Exit codes

| Command family | `0` | `1` | Other non-zero |
|----------------|-----|-----|----------------|
| `python -m finagentbench evaluate/gate/benchmark` | pass | gate/eval failure | CLI/IO error |
| `scripts/run_mutation_suite.py` | 4/4 mutations detected | mutation miss / suite fail | runtime error |
| `scripts/validate_cross_repo.py` | compatibility pass | gate fail | setup/runtime error |
| `scripts/run_rc_validation.py --dry-run` | paths/schema OK | schema/path fail | missing optional fixtures (`3`) |
| `scripts/run_rc_validation.py` (live) | RC pack pass | Agent/gate fail | provider/infra non-pass |

## 1. Minimal offline validation

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

## 2. Full offline validation

```bash
python -m unittest discover -s tests -v
python scripts/run_mutation_suite.py
python scripts/run_correctness_validation.py
python scripts/run_offline_demo.py
python -m unittest tests.test_rc_runner_import -v
```

## 3. Cross-repository gate

Requires sibling `lumenfin-agent` or `LUMENFIN_ROOT`.

```bash
python scripts/validate_cross_repo.py --profile ci
```

## 4. Live RC

Import must stay side-effect free. Prefer dry-run before live:

```bash
python scripts/run_rc_validation.py --help
python scripts/run_rc_validation.py --dry-run
python scripts/run_rc_validation.py
```

Live RC needs configured LumenFin providers. Infrastructure / provider
failures are non-pass and must not be narrated as Agent-quality success.

## 5. Mutation suite

```bash
python scripts/run_mutation_suite.py
```

Expected: 4/4 detections (wrong number, wrong entity, missing citation,
missing risk). Thresholds are not lowered to match an Agent.

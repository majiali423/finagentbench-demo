# Mutation Testing

Mutation testing verifies that the benchmark detects known-bad FinRuns. It is a
test of the evaluator, not a way to tune Agent output.

## Release mutations

| Mutation | Expected detection |
|----------|--------------------|
| `wrong_number` | `numeric_correctness` |
| `wrong_entity` | `entity_coverage` |
| `missing_citation` | `evidence_coverage`, `evidence_consistency` |
| `missing_risk` | `risk_disclosure`, `section_presence` |

Definitions: `benchmarks/mutations/suite.json`.

## Run

```bash
python scripts/run_mutation_suite.py
```

Outputs:

- `outputs/mutation_detection_report.json`
- `outputs/mutation_detection_report.md`

Exit code is non-zero unless all four failures are detected and the clean
baseline has no false positive.

## CI policy

The mutation suite runs on every FinAgentBench push/PR. JSON/Markdown reports
are uploaded as workflow artifacts. Adding a metric does not permit lowering
existing thresholds or removing a mutation.

## Fixture integrity

The suite deep-copies source fixtures before mutation. Release/demo commands
must never rewrite benchmark fixtures.

# Live Semantic Judge Validation

This note records a small live validation of the optional semantic judge. It is
not a production accuracy claim. It checks whether one configured
OpenAI-compatible judge can align with human labels on a small evidence-support
golden subset.

## Command

```powershell
$env:FINAGENTBENCH_LLM_API_KEY = "<provider key>"
python -m finagentbench live-semantic-benchmark benchmarks\semantic_audit\evidence_support_golden.json `
  --limit 10 `
  --endpoint https://api.deepseek.com/chat/completions `
  --model deepseek-chat `
  --cache-path outputs\live-semantic-judge-cache-v2.json `
  --prompt-version evidence_support_live_v2 `
  --out outputs\live-semantic-judge-report-v2.json
Remove-Item Env:FINAGENTBENCH_LLM_API_KEY
```

## Result

- Date: 2026-07-11
- Provider mode: `openai-compatible`
- Model: `deepseek-chat`
- Prompt version: `evidence_support_live_v2`
- Suite: `evidence_support_golden_v1`
- Sample size: 10 cases
- Human-label alignment: 10/10
- False positives: 0
- False negatives: 0

The 10-case subset includes 5 supported summaries and 5 unsupported cases:
unsupported acquisition recommendation, unsupported growth claim, unsupported
valuation claim, wrong-entity evidence, and stale evidence.

## Calibration Finding

The first live run used `evidence_support_live_v1` and exposed an interface
contract issue: the model judged supported cases correctly in its rationale, but
returned scores such as `1.0` instead of a 0-100 score. That made supported
cases fail the benchmark even though the rationale and labels were directionally
correct.

The fix was to make the judge prompt schema explicit: `score` must use a 0-100
scale, `passed=true` only when score is at least 80, and severity must come from
a fixed set. The rerun with `evidence_support_live_v2` aligned with all 10 human
labels.

## Interview Caveat

The static semantic benchmark still measures golden-label replay consistency,
not live LLM accuracy. This live run is a small release-audit smoke test. A
stronger production claim would require 20-50 manually reviewed cases per metric
and repeated runs across prompt/model versions.

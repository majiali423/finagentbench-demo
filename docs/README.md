# FinAgentBench documentation

Start with the [project overview](../README.md) or [中文说明](../README.zh-CN.md).
The published source at
[`40f7599`](https://github.com/majiali423/finagentbench-demo/commit/40f7599e408f317515583405cb90249b811179c0)
includes opt-in scoring v3; the older `v0.1.0-rc.4` package tag remains frozen.
FinRun schema is `1.0`.

## Try and understand

- [Offline demo](../scripts/run_offline_demo.py)
- [Architecture](architecture.md)
- [Metric semantics](METRICS.md)
- [Mutation testing](MUTATION_TESTING.md)
- [CI gates](CI_GATE.md)
- [Validation commands](VALIDATION_COMMANDS.md)
- [LumenFin product evaluation](https://github.com/majiali423/lumenfin-agent/blob/main/docs/evaluation_strategy.md)
  (24-task candidate gold diagnostic + optional LangSmith; FinAgentBench remains layer A, not source accuracy.
  LumenFin scoring policy `lumenfin_eval_contract.v1` uses `evaluate_run` for applicable contract checks.)

## Integrate an Agent

- [FinRun schema](finrun_schema.md)
- [Compatibility policy](FINRUN_COMPATIBILITY.md)
- [Agent integration](agent_integration_guide.md)
- [Adapter guide](adapter_guide.md)
- [Due-diligence integration](due_diligence_integration.md)
- [LumenFin case selection](lumenfin_case_selection.md)
- [LumenFin regression case](lumenfin_regression_case.md)

## Optional audit features

- [Semantic judge validation](live_semantic_judge_validation.md)
- [Human labeling](human_labeling_guide.md)
- [Reference runtime](reference_runtime.md)

## Evidence and history

- [Published v3 source CI](https://github.com/majiali423/finagentbench-demo/actions/runs/34329922587)
- [Frozen rc.4 release evidence](../reports/current/FinAgentBench_Final_Release_Report.md)

Superseded audits, staging plans and early sample reports are available in
[Git history](https://github.com/majiali423/finagentbench-demo/tree/40f7599e408f317515583405cb90249b811179c0/reports/history).

Frozen reports retain their original version and results. They are not a
scoreboard for the current product's answer accuracy.

[MIT license](../LICENSE) · [Third-party notices](../THIRD_PARTY_NOTICES.md)

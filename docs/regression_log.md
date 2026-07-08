# Regression Log

This file records the kinds of failures FinAgentBench is designed to catch. The
examples are fixture-backed so they can be reproduced locally and in CI.

## Missing Entity In Comparative Analysis

- Fixture: `fixtures/fail_finrun.json`
- Case: `fixtures/case_compare_rd.json`
- Failure: AMD is expected by the benchmark case but missing from the run.
- Why it matters: comparative financial answers often look fluent even when one
  company is silently omitted.

## Numeric Formula Regression

- Fixture: `fixtures/fail_finrun.json`
- Failure: NVIDIA R&D intensity does not match `r_and_d / revenue`.
- Why it matters: deterministic financial calculations should be tool-checked,
  not trusted from generated text.

## Market Data Failure Not Disclosed

- Fixture: `fixtures/fail_finrun.json`
- Failure: AMD market data fails but the final answer does not disclose the
  limitation.
- Why it matters: silent provider failures can turn incomplete analysis into
  misleading advice.

## Period And Currency Regressions

- Tests: `tests/test_realistic_fixture.py`
- Failure: a metric mixes FY2025 with FY2024, or USD with EUR.
- Why it matters: real financial analysis often fails through subtle unit,
  currency, and period mismatches rather than obvious syntax errors.

## Citation Number Mismatch

- Test: `tests/test_evidence_consistency.py`
- Failure: a cited source exists, but the numeric value in evidence text does not
  match the metric input used for calculation.
- Why it matters: in due diligence and financial research, a citation is not
  enough if it supports the wrong number.

## Runtime Retry Trace

- Test: `tests/test_reference_runtime.py`
- Scenario: the reference runtime simulates an NVDA market-data rate limit and
  succeeds on retry.
- Why it matters: production agent quality depends on runtime behavior such as
  retry, cache, and tool-call observability, not only final-answer text.

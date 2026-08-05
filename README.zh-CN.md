# FinAgentBench

[English](README.md) | **中文**

FinAgentBench 是一个 **replay-first（先回放）** 的可靠性评测框架。
它独立于 Agent 运行时，只评测已导出的 Agent trace。

[![test](https://github.com/majiali423/finagentbench-demo/actions/workflows/test.yml/badge.svg)](https://github.com/majiali423/finagentbench-demo/actions/workflows/test.yml)

Release `v0.1.0-rc.2`（pre-release）| Package `0.1.0rc2` | FinRun schema `1.0`

[文档索引](docs/README.md) · [指标说明](docs/METRICS.md) ·
[FinRun schema](docs/finrun_schema.md) ·
[验证命令](docs/VALIDATION_COMMANDS.md) ·
[发布报告](reports/current/FinAgentBench_Final_Release_Report.md)

## 为什么要回放 trace？

一份流畅的最终答案仍可能：

- 在对比任务中漏掉一家公司；
- 用错误输入计算比率；
- 引用另一个发行人的证据；
- 隐瞒缺失的市场数据；
- 在“没有任何可检查项”时仍被评测器放行。

只看最终答案，不足以判断金融 Agent 的可靠性。

## 工作方式

```text
FinRun 导出
    → adapter / schema 校验
    → 确定性指标（+ 可选语义 judge）
    → Findings + EvalReport
    → CI 通过 / 失败
```

Case contract 决定哪些字段必须可检查。分数取决于导出 trace 的可观测性。
默认发布路径以确定性指标为主；语义 judge 仍为可选项。

## 最小 FinRun

任何框架都可以产出该工件；已提供 LumenFin 与通用 Agent state 的 adapter。

```json
{
  "schema_version": "1.0",
  "run_id": "demo-001",
  "query": "Compare Company A and Company B",
  "entities": [{"name": "Company A"}, {"name": "Company B"}],
  "steps": [{"name": "retrieval", "status": "ok"}],
  "metrics": [],
  "evidence": [],
  "market_data": [],
  "final_output": "Research output with disclosed limitations."
}
```

Case 决定哪些字段必须可检查。当启用 `require_checkable_metrics` 时，空列表
不会自动得满分。

字段说明见 [docs/finrun_schema.md](docs/finrun_schema.md) 与
[docs/FINRUN_COMPATIBILITY.md](docs/FINRUN_COMPATIBILITY.md)。

## Finding 长什么样

以下摘自对内置 known-fail fixture 的评测
（`fixtures/fail_due_diligence_finrun.json`，退出码 `1`）：

```json
{
  "run_id": "fail-dd-targetco",
  "score": 0.0,
  "passed": false,
  "metrics": [
    {
      "name": "numeric_correctness",
      "score": 0.0,
      "passed": false,
      "findings": [
        {
          "metric": "numeric_correctness",
          "severity": "high",
          "message": "TargetCo debt_to_assets mismatch: expected 0.4, got 0.5",
          "recommendation": "Recompute financial ratios with deterministic tools instead of relying on model text."
        }
      ]
    },
    {
      "name": "evidence_consistency",
      "score": 50.0,
      "passed": false,
      "findings": [
        {
          "metric": "evidence_consistency",
          "severity": "high",
          "message": "TargetCo debt_to_assets input total_liabilities=120.0 is not supported by numeric evidence.",
          "recommendation": "Check that cited evidence text contains the same financial input values used by the calculation."
        }
      ]
    }
  ]
}
```

每次运行还会同时产出 Markdown 与 HTML 报告。

## 指标

默认确定性 CI 覆盖：

- 实体覆盖与实体泄漏；
- 数值正确性；
- 单位/币种与时间一致性；
- Case 驱动的输入值合理性（仅有限区间）；
- 证据覆盖与一致性；
- 检索 / 期间 provenance；
- 必要执行步骤与报告章节；
- 风险披露与合规用语。

Opt-in 指标：

- visible output integrity（需要 `"scoring_version": "2"`；零权重，靠 high
  severity 阻断）；
- 语义 judge（evidence support、risk quality、compliance）— 仅用于 audit
  profile，不进入确定性发布证据。

详见 [Metrics](docs/METRICS.md) 与
[FinRun compatibility](docs/FINRUN_COMPATIBILITY.md)。

## 核心 mutation

CI mutation 门禁必须检出以下四类可靠性失败：

1. wrong number（错误数值）
2. wrong entity（错误实体）
3. missing citation（缺失引用）
4. missing risk（缺失风险披露）

套件将其报告为 **Core reliability mutations: 4/4**。

## 扩展 mutation

扩展的 provenance / period 负向对照单独按控并单独计数，不并入核心四项：

- missing metric period provenance
- query-period source
- assumed period alignment
- missing source record / citation
- formula cross-period inputs
- missing period alignment
- metric-period drift

详情见 [docs/MUTATION_TESTING.md](docs/MUTATION_TESTING.md)。

## LumenFin 集成

将 `lumenfin-agent` 克隆为同级目录，或设置环境变量：

```bash
export LUMENFIN_ROOT=/path/to/lumenfin-agent
export FINAGENTBENCH_DIR=/path/to/finagentbench-demo
python scripts/validate_cross_repo.py --profile ci
```

已对冻结的 LumenFin `v0.1.0-rc.2`
（`d075b6851739be82ec2fb71fea7ad08d92d76511`）验证，FinRun schema `1.0`。

摘要会记录双方仓库 commit、worktree 状态、FinRun schema、benchmark profile，
以及 core / extended mutation 结果。

跨仓 Release Candidate 编排：

```bash
python scripts/run_rc_validation.py --help
python scripts/run_rc_validation.py --dry-run      # 仅检查路径、fixture、schema
python scripts/run_rc_validation.py --offline-only # 确定性门禁，不调用 live Agent
```

不带 `--offline-only` 运行时需要已配置的 LumenFin provider。
基础设施失败属于 non-pass，不得叙述为 Agent 质量成功。

## 快速开始

需要 Python 3.11+（CI 验证 3.11 与 3.12）。本节全部命令均为确定性离线路径：
无需 API key，也无需网络访问。

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m unittest discover -s tests -v
```

评测内置的合成尽调样本：

```bash
python -m finagentbench evaluate \
  fixtures/pass_due_diligence_finrun.json \
  --case fixtures/case_due_diligence.json \
  --profile ci \
  --out outputs/example
```

`evaluate` / `gate` / `benchmark` 退出码：

| Code | Meaning |
|------|---------|
| `0` | 评测 / 门禁通过 |
| `1` | 评测 / 门禁失败（known-fail fixture 预期如此） |
| 其他非零 | CLI / IO / 参数错误 |

免密钥发布演示：

```bash
python scripts/run_offline_demo.py
```

Mutation 与正确性门禁：

```bash
python scripts/run_mutation_suite.py
python scripts/run_correctness_validation.py
```

支持的验证命令见 [docs/VALIDATION_COMMANDS.md](docs/VALIDATION_COMMANDS.md)。

## 已验证结果（`v0.1.0-rc.2`）

| Gate | Result |
|------|--------|
| Unit tests | 127 PASS |
| Offline demo | PASS |
| Correctness validation | PASS |
| Core reliability mutations | 4/4 |
| Extended provenance/period mutations | 7/7 |
| Total negative controls | 11/11 |
| LumenFin `v0.1.0-rc.2` cross-repo | PASS |

以上门禁均可离线复现，并在 GitHub Actions 中运行（Python 3.11 smoke lane、
Python 3.12 full lane，含 mutation suite 以及 pin 到公开 LumenFin tag 的跨仓检查）。

证据：
[reports/current/FinAgentBench_Final_Release_Report.md](reports/current/FinAgentBench_Final_Release_Report.md)。

## Benchmark 诚信原则

- 不会为了匹配某个被测 Agent 而降低指标阈值。
- 必填检查项为空时 fail closed，并给出诊断 finding。
- 不支持的 FinRun schema 与 scoring version 会在评分前被拒绝。
- Case hash 与启用的指标会写入 EvalReport。
- 通过评测不等于投资质量；仍需人工财务审阅。

## 局限

FinAgentBench **不是**：

- 学术排行榜；
- 普遍事实正确性证明；
- 投资表现评估器；
- 生产就绪认证。

范围边界：

- Case contract 决定评测要求，因此分数强度取决于 case 与导出 trace。
- 本版本中 Claim–Evidence Binding **尚未**成为独立指标；引用相关检查由证据与
  provenance 指标间接覆盖。
- 可选语义 judge 会引入 provider 波动，不纳入发布证据。
- 仍需人工财务审阅。

## 仓库结构

```text
finagentbench/    评测器、adapter、指标与报告模型
benchmarks/       确定性套件、mutation 与语义金标数据
fixtures/         合成 FinRun 与 case contract
tests/            单元与跨项目回归测试
scripts/          受支持的发布与验证入口
docs/             schema、指标、集成与 CI 指南
reports/current/  当前发布证据
reports/history/  已归档的工程证据
examples/         脱敏演示工件
tools/            已归档、不受支持的审计脚本
```

## 文档地图

| Doc | Purpose |
|-----|---------|
| [docs/README.md](docs/README.md) | 文档索引 |
| [docs/architecture.md](docs/architecture.md) | 评测器架构 |
| [docs/finrun_schema.md](docs/finrun_schema.md) | FinRun 字段说明 |
| [docs/FINRUN_COMPATIBILITY.md](docs/FINRUN_COMPATIBILITY.md) | 生产者 / schema 支持矩阵 |
| [docs/METRICS.md](docs/METRICS.md) | 指标定义与阈值治理 |
| [docs/MUTATION_TESTING.md](docs/MUTATION_TESTING.md) | 核心与扩展负向对照 |
| [docs/CI_GATE.md](docs/CI_GATE.md) | CI lane 与失败分类 |
| [docs/agent_integration_guide.md](docs/agent_integration_guide.md) | 接入新 Agent |
| [docs/adapter_guide.md](docs/adapter_guide.md) | 编写 adapter |
| [docs/VALIDATION_COMMANDS.md](docs/VALIDATION_COMMANDS.md) | 支持的命令与退出码 |
| [CHANGELOG.md](CHANGELOG.md) | 版本历史 |

## 许可状态

尚未选择开源许可证：仓库以 source-available 形式供审阅与评估，**不授予**再分发
或生产使用权利。评测输出仅用于工程评估，不构成投资建议。

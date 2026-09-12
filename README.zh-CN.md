# FinAgentBench
**回放财务 Agent 的输出，解释哪些断言没有通过验证。**

[English](README.md) | **中文**

FinAgentBench 是 [LumenFin](https://github.com/majiali423/lumenfin-agent)
项目的评测组件。它读取 **FinRun 1.0** 导出，按显式 case 检查，
输出指标级问题以及 JSON、Markdown、HTML 报告。
回放导出文件不需要再次运行原 Agent。

[![test](https://github.com/majiali423/finagentbench-demo/actions/workflows/test.yml/badge.svg)](https://github.com/majiali423/finagentbench-demo/actions/workflows/test.yml)

[运行示例](#运行示例) · [评分逻辑](#一次评测如何执行) ·
[接入其他 Agent](docs/agent_integration_guide.md) · [文档索引](docs/README.md)

## 评测器解决什么问题

内部指标正确，最终报告仍可能写错百分比、公司或财年。
FinAgentBench 同时检查结构化数据和可见输出：

| 层次 | 检查输入 | 要回答的问题 |
|---|---|---|
| 契约 | FinRun + case | 结构、评分版本和用例要求是否有效 |
| 结构化证据 | 公式输入、指标、实体、引用 | 能否复算，身份是否一致，证据是否齐全 |
| 可见输出：显式启用 v3 | 正文、表格、Claim Ledger | 受支持的财务数字、单位、期间、比较关系及引用是否匹配 |
| 门禁 | 指标结果 + 严重性规则 | 加权分和阻断问题是否满足 case 要求 |

证据期间未知，不能支持一个确定财年的断言。
总分再高，也不能抵消 case 明确要求阻断的严重问题。
FinAgentBench 不能替代 LumenFin 的文档任务目录。那 24 题是开发诊断用的候选 gold（派生摘录、lexical 检索）。内部字段与可见回答写成同一个错误数字时，导出检查仍可能通过，而目录检查必须失败。A 层不是正式原文准确率。LumenFin 接入策略 `lumenfin_eval_contract.v1` 通过完整 `evaluate_run` 执行适用指标，缺主体时不得默认 NVIDIA，Bench 不可用或报错不得计为通过。

## 一次评测如何执行

```text
Agent 状态 / FinRun
  → Adapter 与 Schema 校验
  → 绑定 case 预先规定的公司与检查要求
  → 执行启用的指标
  → 汇总得分并检查阻断问题
  → EvalReport + 问题定位 + CI 结果
```

### 用版本化输入隔离生成器与评分器

[Schema](finagentbench/schema.py)定义运行记录、证据、指标和问题结构。
[Adapters](finagentbench/adapters/)统一不同生成器的输出，
指标代码无需导入 Agent 的图或 API。

预期行为由 case 定义。质量用例的公司集合必须来自测试规格，
不能由 Agent 本次输出的公司集合反向决定。
[Case binding](finagentbench/case_binding.py)明确区分质量评测与兼容性冒烟检查。

### 确定性校验，并保留可检查的失败原因

[Runner](finagentbench/runner.py)校验输入、选择指标、计算加权结果，
再应用 `block_on_severity`。
[数值正确性](finagentbench/metrics/numeric.py)检查结构化公式结果。

[Visible supported claims](finagentbench/metrics/visible_supported_claims.py)
解析受支持的财务断言，并与导出证据比较。
它有明确的财务词表与语法范围，未覆盖的自由叙述需要另外审阅，
不能把解析器得分解释成所有文本的事实正确率。

[产品用例](fixtures/case_lumenfin_product_quality_v1.json)显式启用 v3：

```json
{
  "scoring_version": "3",
  "enabled_metrics": ["visible_supported_claims", "numeric_correctness", "entity_coverage"],
  "require_checkable_metrics": true,
  "require_visible_claim_citations": true,
  "block_on_severity": ["high", "critical"]
}
```

上面仅为配置节选，运行时使用链接中的完整 case。

### 用故意写错的输出检查评分器本身

[突变测试](docs/MUTATION_TESTING.md)从正确 trace 出发，定向修改内容，
检查评测器是否识别出对应问题。
[突变集](benchmarks/mutations/suite.json)包含数值、公司、引用和来源/期间控制。

CI 同时运行正例与负例。负例必须产生新的评测报告，
报告的 run ID 要匹配，`passed=false`，退出状态也必须符合预期。
程序崩溃不能算作成功拦截。见[工作流](.github/workflows/test.yml)。

## 运行示例

使用 Python **3.11+**：

```bash
git clone https://github.com/majiali423/finagentbench-demo.git
cd finagentbench-demo
python -m venv .venv
```

PowerShell 激活：`.\.venv\Scripts\Activate.ps1`。
POSIX 激活：`source .venv/bin/activate`。

```bash
python -m pip install -e .
python scripts/run_offline_demo.py
python -m finagentbench evaluate fixtures/product_quality_visible_baseline_finrun.json --case fixtures/case_lumenfin_product_quality_v1.json --profile ci --out outputs/visible
```

打开输出报告，查看每项指标与问题定位。
离线示例无需 API key 或模型调用。检查负例和单元测试：

```bash
python scripts/run_mutation_suite.py
python -m unittest discover -s tests -v
```

[验证命令](docs/VALIDATION_COMMANDS.md)包含跨仓检查及可选 live 路径。
[已通过的 CI](https://github.com/majiali423/finagentbench-demo/actions/runs/34340092459)
覆盖 Python 3.11 与 3.12。

## 如何用于产品评测

FinAgentBench 检查的是给定 run 与 case。
要评价产品回答质量，还需要从原始材料独立建立 gold 答案和证据，
不能只相信生成器自己导出的指标。

[LumenFin 评测方案](https://github.com/majiali423/lumenfin-agent/blob/main/docs/evaluation_strategy.md)
分别衡量任务成功、证据支持、拒答、检索诊断、评分器突变检测和执行成本。
新的文档任务集与基线执行器属于待实施方案，fixture 门禁分不作为已测产品准确率展示。

两个仓库由同一作者维护。FinRun 边界让评测器可审查、可复用，
不代表第三方独立评测。

## 代码与兼容性

| 入口 | 内容 |
|---|---|
| [Schema](docs/finrun_schema.md) | 导出契约 |
| [Adapter 指南](docs/adapter_guide.md) | 接入其他生成器 |
| [指标语义](docs/METRICS.md) | 范围、容差和问题规则 |
| [Runner](finagentbench/runner.py) | 执行评测与基线比较 |
| [CI 门禁](docs/CI_GATE.md) | 正例、负例与发布检查 |

FinRun schema 为 `1.0`；默认评分仍是 v1，v3 按 case 启用。
包元数据 `0.1.0rc4`、冻结标签 `v0.1.0-rc.4` 与评分版本分开管理，
该标签早于 v3。LumenFin 产品门禁固定已发布的 v3 评分器源码，
rc.3/rc.4 两条路径用于冻结兼容性检查。
见[兼容性策略](docs/FINRUN_COMPATIBILITY.md)。

[MIT 许可证](LICENSE) · [第三方声明](THIRD_PARTY_NOTICES.md)。
评测结果用于辅助人工审阅财务研究输出。

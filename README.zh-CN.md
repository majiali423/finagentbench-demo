# FinAgentBench

[English](README.md) | **中文**

**回放 Agent 的答案与证据，定位缺乏依据的财务断言。**
FinAgentBench 接收 **FinRun 1.0** 导出，生成问题定位、报告和 CI 通过/失败结果，
无需执行 Agent 本身。

[![test](https://github.com/majiali423/finagentbench-demo/actions/workflows/test.yml/badge.svg)](https://github.com/majiali423/finagentbench-demo/actions/workflows/test.yml)

[快速体验](#快速体验) · [指标](docs/METRICS.md) ·
[FinRun schema](docs/finrun_schema.md) · [文档索引](docs/README.md)

## 检查什么

| 层次 | 示例 |
|---|---|
| 执行轨迹与证据 | 漏掉公司、计算输入不一致、缺引用、缺少必需检查 |
| 可见断言：显式启用 v3 | 正文、表格、Claim Ledger 中错误的数字、单位、币种、期间或来源 |
| 负向对照 | 故意改错数字/主体或移除引用/风险说明，必须被拦截 |

期间未知的证据不能支持具体年份的断言。内部指标正确，也不能抵消最终回答中的矛盾。

```text
FinRun → schema / adapter → 确定性检查 → 问题定位与报告 → CI 门禁
```

## 快速体验

需要 Python **3.11+**，CI 覆盖 3.11 与 3.12。
安装会下载构建依赖，以下演示不需要 API key 或在线模型调用。

```bash
git clone https://github.com/majiali423/finagentbench-demo.git
cd finagentbench-demo
python -m venv .venv
```

PowerShell 激活：`.\.venv\Scripts\Activate.ps1`。
POSIX shell 激活：`source .venv/bin/activate`。

```bash
python -m pip install -e .
python scripts/run_offline_demo.py
```

查看生成的 JSON、Markdown 和 HTML 报告。显式运行可见输出 v3 基线：

```bash
python -m finagentbench evaluate fixtures/product_quality_visible_baseline_finrun.json --case fixtures/case_lumenfin_product_quality_v1.json --profile ci --out outputs/visible
```

问题定位会指出指标与错误原因，例如：

```text
NVIDIA operating_income is stated for FY2025 but verified period is unknown.
```

退出码 **0** 表示通过，**1** 表示未通过（错误 fixture 的预期结果），
其他非零值表示命令或执行错误。

## 为什么单独维护评测仓？

[LumenFin](https://github.com/majiali423/lumenfin-agent) 生成答案，
FinAgentBench 评测导出产物。版本化边界使生成端、评分器及兼容性变更可以分别审查。
其他 Agent 也可以实现同一 [FinRun 接口](docs/agent_integration_guide.md)。

两个仓库由同一作者维护。它们提供作者自有的契约门禁；
分仓或高分本身不构成第三方验证，也不等于真实问题准确率。

## 评分与发布版本

评分版本、Python 包版本和 FinRun schema 分别管理。

| 用途 | 版本 / 证据 |
|---|---|
| 包含 scoring v3 的已发布源码 | [`40f7599`](https://github.com/majiali423/finagentbench-demo/commit/40f7599e408f317515583405cb90249b811179c0) |
| 历史包与标签 | `0.1.0rc4` / `v0.1.0-rc.4`；冻结标签早于 v3 |
| FinRun 外层协议 | `1.0` |
| 默认评分 | v1，保留原有 case 语义 |
| 可见输出评分 | 显式配置 v3，并启用 `visible_supported_claims` |
| 冻结生成端兼容性 | 本仓完整 CI 使用 LumenFin `v0.1.0-rc.3` |

[`40f7599` 的 2026-09-09 CI](https://github.com/majiali423/finagentbench-demo/actions/runs/34329922587)
已通过。LumenFin 的
[Product quality v3 门禁](https://github.com/majiali423/lumenfin-agent/actions/runs/34329999879)
固定使用该评分器提交，rc.3/rc.4 评分器仍用于冻结契约兼容性。

详细规则见[指标语义](docs/METRICS.md)与[兼容策略](docs/FINRUN_COMPATIBILITY.md)。
历史 rc.4 结果保留在[发布报告](reports/current/FinAgentBench_Final_Release_Report.md)。

## 验证

```bash
python -m unittest discover -s tests -v
python scripts/run_mutation_suite.py
python scripts/run_correctness_validation.py
```

联合检查需要安装当前 LumenFin 源码，显式配置
`LUMENFIN_ROOT` / `FINAGENTBENCH_DIR`，再运行
`python scripts/validate_cross_repo.py --profile ci`。
[验证命令](docs/VALIDATION_COMMANDS.md)说明环境配置与可选在线 RC 路径。

## 能力边界

- Case 定义必需检查与阈值；必需检查没有可检查项时失败，未知协议或评分版本会被拒绝。
- v3 覆盖支持范围内的财务断言语法，不证明任意自然语言的真实性。
  语义 judge 为可选项，不纳入确定性发布证据。
- 突变检出率和冻结契约分只反映相应用例，不评估投资收益，也不认证生产就绪。
- 来源质量与财务结论仍需人工审查。

## 目录导览

| 路径 | 职责 |
|---|---|
| `finagentbench/` | 协议、适配器、指标、报告与命令行 |
| `benchmarks/`、`fixtures/` | 用例及负向对照 |
| `tests/` | 单测、回归及兼容性验证 |
| `scripts/` | 正式演示和验证入口 |
| `docs/` | 指标、接入与运行说明 |
| `reports/` | 版本化发布证据与历史记录 |

项目自有代码采用 [MIT](LICENSE) 许可证；
外部依赖和输入遵循[第三方声明](THIRD_PARTY_NOTICES.md)。

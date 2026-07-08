from __future__ import annotations

import json
from dataclasses import asdict
from html import escape
from pathlib import Path
from typing import Any

from .schema import EvalReport


def write_eval_report(report: EvalReport, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = asdict(report)
    json_path = out_dir / f"{report.run_id}_eval_report.json"
    md_path = out_dir / f"{report.run_id}_eval_report.md"
    html_path = out_dir / f"{report.run_id}_eval_report.html"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    html_path.write_text(_render_html(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path), "html": str(html_path)}


def write_compare_report(payload: dict[str, Any], out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "compare_report.json"
    md_path = out_dir / "compare_report.md"
    html_path = out_dir / "compare_report.html"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# FinAgentBench Compare Report",
        "",
        f"Baseline: `{payload['baseline_run_id']}` score={payload['baseline_score']}",
        f"Current: `{payload['current_run_id']}` score={payload['current_score']}",
        f"Delta: `{payload['score_delta']}`",
        f"Status: **{'PASS' if payload['passed'] else 'FAIL'}**",
        "",
        "## Regressions",
    ]
    if payload["regressions"]:
        for name, delta in payload["regressions"].items():
            lines.append(f"- `{name}` dropped by {abs(delta)} points")
    else:
        lines.append("- None")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    html_path.write_text(_render_compare_html(payload), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path), "html": str(html_path)}


def _render_markdown(report: EvalReport) -> str:
    lines = [
        "# FinAgentBench Evaluation Report",
        "",
        f"Run: `{report.run_id}`",
        f"Score: **{report.score}**",
        f"Status: **{'PASS' if report.passed else 'FAIL'}**",
        "",
        "## Metrics",
    ]
    for metric in report.metrics:
        lines.append(f"### {metric.name}")
        lines.append(f"- Score: `{metric.score}`")
        lines.append(f"- Passed: `{metric.passed}`")
        if metric.findings:
            lines.append("- Findings:")
            for finding in metric.findings:
                lines.append(f"  - [{finding.severity}] {finding.message}")
        else:
            lines.append("- Findings: none")
        lines.append("")
    return "\n".join(lines)


def _render_html(report: EvalReport) -> str:
    status = "PASS" if report.passed else "FAIL"
    metric_rows = []
    for metric in report.metrics:
        findings = "<br>".join(
            escape(f"[{finding.severity}] {finding.message}") for finding in metric.findings
        ) or "none"
        metric_rows.append(
            "<tr>"
            f"<td>{escape(metric.name)}</td>"
            f"<td>{metric.score}</td>"
            f"<td>{metric.passed}</td>"
            f"<td>{findings}</td>"
            "</tr>"
        )
    return _html_page(
        "FinAgentBench Evaluation Report",
        f"""
        <h1>FinAgentBench Evaluation Report</h1>
        <p><strong>Run:</strong> {escape(report.run_id)}</p>
        <p><strong>Score:</strong> {report.score}</p>
        <p><strong>Status:</strong> <span class="{status.lower()}">{status}</span></p>
        <table>
          <thead><tr><th>Metric</th><th>Score</th><th>Passed</th><th>Findings</th></tr></thead>
          <tbody>{''.join(metric_rows)}</tbody>
        </table>
        """,
    )


def _render_compare_html(payload: dict[str, Any]) -> str:
    status = "PASS" if payload["passed"] else "FAIL"
    regression_rows = []
    for name, delta in payload["regressions"].items():
        regression_rows.append(f"<tr><td>{escape(name)}</td><td>{delta}</td></tr>")
    body = "".join(regression_rows) or "<tr><td colspan='2'>none</td></tr>"
    return _html_page(
        "FinAgentBench Compare Report",
        f"""
        <h1>FinAgentBench Compare Report</h1>
        <p><strong>Baseline:</strong> {escape(payload['baseline_run_id'])} score={payload['baseline_score']}</p>
        <p><strong>Current:</strong> {escape(payload['current_run_id'])} score={payload['current_score']}</p>
        <p><strong>Delta:</strong> {payload['score_delta']}</p>
        <p><strong>Status:</strong> <span class="{status.lower()}">{status}</span></p>
        <table>
          <thead><tr><th>Metric</th><th>Delta</th></tr></thead>
          <tbody>{body}</tbody>
        </table>
        """,
    )


def _html_page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #172026; }}
    h1 {{ font-size: 24px; margin-bottom: 16px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
    th, td {{ border: 1px solid #d8dee4; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f6f8fa; }}
    .pass {{ color: #116329; font-weight: 700; }}
    .fail {{ color: #a40e26; font-weight: 700; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""

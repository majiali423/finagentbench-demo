from __future__ import annotations

import ast
import math
from typing import Any

from ..schema import Finding, MetricResult


def numeric_correctness(run: dict[str, Any], case: dict[str, Any]) -> MetricResult:
    tolerance = float(case.get("numeric_tolerance", 0.001))
    findings: list[Finding] = []
    checked = 0
    passed = 0
    for metric in run.get("metrics", []):
        formula = metric.get("formula")
        inputs = metric.get("inputs") or {}
        if not formula or not inputs:
            continue
        checked += 1
        expected = _safe_eval_formula(formula, inputs)
        actual = float(metric.get("value"))
        if expected is not None and math.isclose(expected, actual, abs_tol=tolerance):
            passed += 1
            continue
        findings.append(
            Finding(
                metric="numeric_correctness",
                severity="high",
                message=(
                    f"{metric.get('entity')} {metric.get('name')} mismatch: "
                    f"expected {expected}, got {actual}"
                ),
                recommendation="Recompute financial ratios with deterministic tools instead of relying on model text.",
            )
        )
    score = 100.0 if checked == 0 else round(passed / checked * 100, 2)
    return MetricResult("numeric_correctness", score, not findings, findings)


def _safe_eval_formula(formula: str, inputs: dict[str, Any]) -> float | None:
    try:
        tree = ast.parse(formula, mode="eval")
        evaluator = _SafeFormulaEvaluator({key: float(value) for key, value in inputs.items()})
        return round(evaluator.visit(tree), 6)
    except Exception:
        return None


class _SafeFormulaEvaluator(ast.NodeVisitor):
    allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.Load,
        ast.Name,
        ast.Constant,
        ast.UnaryOp,
        ast.USub,
    )

    def __init__(self, variables: dict[str, float]) -> None:
        self.variables = variables

    def visit(self, node: ast.AST) -> float:
        if not isinstance(node, self.allowed_nodes):
            raise ValueError(f"Unsafe node: {type(node).__name__}")
        return super().visit(node)

    def visit_Expression(self, node: ast.Expression) -> float:
        return self.visit(node.body)

    def visit_BinOp(self, node: ast.BinOp) -> float:
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left**right
        raise ValueError("Unsupported operator")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> float:
        if isinstance(node.op, ast.USub):
            return -self.visit(node.operand)
        raise ValueError("Unsupported unary operator")

    def visit_Name(self, node: ast.Name) -> float:
        return self.variables[node.id]

    def visit_Constant(self, node: ast.Constant) -> float:
        if not isinstance(node.value, (int, float)):
            raise ValueError("Only numeric constants are allowed")
        return float(node.value)

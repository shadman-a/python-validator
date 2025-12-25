from __future__ import annotations

from typing import Any

from ..core.models import Issue


def run(df_left, df_right, rule: dict, run_id: str, mode: str) -> tuple[list[Issue], set[int], set[int]]:
    issues: list[Issue] = []
    missing_left: list[str] = []
    missing_right: list[str] = []
    if mode == "compare":
        cols = rule.get("columns", {})
        left_cols = cols.get("left", [])
        right_cols = cols.get("right", [])
        missing_left = [col for col in left_cols if col not in df_left.columns]
        missing_right = [col for col in right_cols if col not in df_right.columns]
    else:
        cols = rule.get("columns", [])
        missing_left = [col for col in cols if col not in df_left.columns]
    severity = rule.get("severity", "ERROR")
    for col in missing_left:
        issues.append(
            Issue(
                run_id=run_id,
                issue_id=f"missing_left_{col}",
                severity=severity,
                issue_type="MISSING_COLUMN",
                message=f"Missing required column {col} in left file",
                file_side="LEFT" if mode == "compare" else "SINGLE",
                column=col,
            )
        )
    for col in missing_right:
        issues.append(
            Issue(
                run_id=run_id,
                issue_id=f"missing_right_{col}",
                severity=severity,
                issue_type="MISSING_COLUMN",
                message=f"Missing required column {col} in right file",
                file_side="RIGHT",
                column=col,
            )
        )
    return issues, set(), set()

from __future__ import annotations

import polars as pl

from ..core.models import Issue


def run(df_left, df_right, rule: dict, run_id: str, mode: str):
    expr = rule.get("expression")
    severity = rule.get("severity", "WARN")
    if not expr:
        return [], set(), set()
    try:
        mask = df_left.select(pl.sql_expr(expr)).to_series().fill_null(False)
    except Exception:
        return [], set(), set()
    issues: list[Issue] = []
    bad_rows: set[int] = set()
    for row_idx, is_bad in enumerate(mask.to_list()):
        if not is_bad:
            continue
        if len(issues) >= 5000:
            break
        issues.append(
            Issue(
                run_id=run_id,
                issue_id=f"row_rule_{row_idx}",
                severity=severity,
                issue_type="ROW_RULE",
                message=rule.get("message", "Row rule failed"),
                file_side="SINGLE" if mode == "single" else "LEFT",
                row_index=row_idx,
            )
        )
        bad_rows.add(row_idx)
    return issues, bad_rows, set()

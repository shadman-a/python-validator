from __future__ import annotations

import re

from ..core.models import Issue

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _is_int(value: str) -> bool:
    return value.isdigit()


def _is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def run(df_left, df_right, rule: dict, run_id: str, mode: str):
    column = rule.get("column")
    check_type = rule.get("check")
    severity = rule.get("severity", "WARN")
    if not column or column not in df_left.columns:
        return [], set(), set()
    series = df_left[column].cast(str).fill_null("")
    issues: list[Issue] = []
    bad_rows: set[int] = set()
    for row_idx, value in enumerate(series.to_list()):
        if value == "":
            continue
        ok = True
        if check_type == "integer":
            ok = _is_int(value)
        elif check_type == "float":
            ok = _is_float(value)
        elif check_type == "email":
            ok = EMAIL_RE.match(value) is not None
        elif check_type == "date":
            ok = DATE_RE.match(value) is not None
        if ok:
            continue
        if len(issues) >= 5000:
            break
        issues.append(
            Issue(
                run_id=run_id,
                issue_id=f"type_{column}_{row_idx}",
                severity=severity,
                issue_type="TYPE_MISMATCH",
                message=f"Value does not match type {check_type} in {column}",
                file_side="SINGLE" if mode == "single" else "LEFT",
                row_index=row_idx,
                column=column,
                left_value=value,
            )
        )
        bad_rows.add(row_idx)
    return issues, bad_rows, set()

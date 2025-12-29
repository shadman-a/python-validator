from __future__ import annotations

import re

from ..core.models import Issue


def run(df_left, df_right, rule: dict, run_id: str, mode: str):
    column = rule.get("column")
    pattern = rule.get("pattern")
    severity = rule.get("severity", "WARN")
    if not column or not pattern or column not in df_left.columns:
        return [], set(), set()
    regex = re.compile(pattern)
    series = df_left[column].cast(str).fill_null("")
    issues: list[Issue] = []
    bad_rows: set[int] = set()
    for row_idx, value in enumerate(series.to_list()):
        if regex.match(value):
            continue
        if len(issues) >= 5000:
            break
        issues.append(
            Issue(
                run_id=run_id,
                issue_id=f"regex_{column}_{row_idx}",
                severity=severity,
                issue_type="REGEX_MISMATCH",
                message=f"Value does not match regex for {column}",
                file_side="SINGLE" if mode == "single" else "LEFT",
                row_index=row_idx,
                column=column,
                left_value=value,
            )
        )
        bad_rows.add(row_idx)
    return issues, bad_rows, set()

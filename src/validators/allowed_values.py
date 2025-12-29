from __future__ import annotations

from ..core.models import Issue


def run(df_left, df_right, rule: dict, run_id: str, mode: str):
    column = rule.get("column")
    allowed = set(rule.get("values", []))
    severity = rule.get("severity", "WARN")
    if not column or column not in df_left.columns:
        return [], set(), set()
    series = df_left[column].cast(str).fill_null("")
    issues: list[Issue] = []
    bad_rows: set[int] = set()
    for row_idx, value in enumerate(series.to_list()):
        if value in allowed:
            continue
        if len(issues) >= 5000:
            break
        issues.append(
            Issue(
                run_id=run_id,
                issue_id=f"allowed_{column}_{row_idx}",
                severity=severity,
                issue_type="DISALLOWED_VALUE",
                message=f"Value not allowed in {column}",
                file_side="SINGLE" if mode == "single" else "LEFT",
                row_index=row_idx,
                column=column,
                left_value=value,
            )
        )
        bad_rows.add(row_idx)
    return issues, bad_rows, set()

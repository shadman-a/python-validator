from __future__ import annotations

from ..core.models import Issue


def _check(df, columns: list[str], run_id: str, severity: str, side: str) -> tuple[list[Issue], set[int]]:
    issues: list[Issue] = []
    bad_rows: set[int] = set()
    for column in columns:
        if column not in df.columns:
            continue
        null_mask = df[column].is_null() | (df[column].cast(str).str.strip_chars().eq(""))
        idx = df.select(null_mask).to_series().to_list()
        for row_idx, is_bad in enumerate(idx):
            if not is_bad:
                continue
            if len(issues) >= 5000:
                break
            issues.append(
                Issue(
                    run_id=run_id,
                    issue_id=f"null_{side}_{column}_{row_idx}",
                    severity=severity,
                    issue_type="NULL_VALUE",
                    message=f"Null or blank value in {column}",
                    file_side=side,
                    row_index=row_idx,
                    column=column,
                )
            )
            bad_rows.add(row_idx)
    return issues, bad_rows


def run(df_left, df_right, rule: dict, run_id: str, mode: str):
    severity = rule.get("severity", "WARN")
    if mode == "compare":
        cols = rule.get("columns", {})
        left_cols = cols.get("left", [])
        right_cols = cols.get("right", [])
        issues_left, bad_left = _check(df_left, left_cols, run_id, severity, "LEFT")
        issues_right, bad_right = _check(df_right, right_cols, run_id, severity, "RIGHT")
        return issues_left + issues_right, bad_left, bad_right
    cols = rule.get("columns", [])
    issues, bad = _check(df_left, cols, run_id, severity, "SINGLE")
    return issues, bad, set()

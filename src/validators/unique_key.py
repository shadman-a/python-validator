from __future__ import annotations

from ..core.models import Issue


def _check(df, column: str, run_id: str, severity: str, side: str):
    if column not in df.columns:
        return [], set()
    series = df[column]
    dup_mask = series.is_duplicated()
    idx = dup_mask.to_list()
    issues: list[Issue] = []
    bad_rows: set[int] = set()
    for row_idx, is_dup in enumerate(idx):
        if not is_dup:
            continue
        if len(issues) >= 5000:
            break
        issues.append(
            Issue(
                run_id=run_id,
                issue_id=f"dup_{side}_{column}_{row_idx}",
                severity=severity,
                issue_type="DUPLICATE_KEY",
                message=f"Duplicate key in {column}",
                file_side=side,
                row_index=row_idx,
                column=column,
                record_key=str(series[row_idx]) if series[row_idx] is not None else None,
            )
        )
        bad_rows.add(row_idx)
    return issues, bad_rows


def run(df_left, df_right, rule: dict, run_id: str, mode: str):
    severity = rule.get("severity", "ERROR")
    if mode == "compare":
        key = rule.get("key", {})
        left_key = key.get("left")
        right_key = key.get("right")
        issues_left, bad_left = _check(df_left, left_key, run_id, severity, "LEFT")
        issues_right, bad_right = _check(df_right, right_key, run_id, severity, "RIGHT")
        return issues_left + issues_right, bad_left, bad_right
    key = rule.get("key")
    issues, bad = _check(df_left, key, run_id, severity, "SINGLE")
    return issues, bad, set()

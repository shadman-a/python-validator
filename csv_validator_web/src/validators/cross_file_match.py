from __future__ import annotations

from ..core.models import Issue


def run(df_left, df_right, rule: dict, run_id: str, mode: str):
    if mode != "compare":
        return [], set(), set()
    key = rule.get("key", {})
    left_key = key.get("left")
    right_key = key.get("right")
    severity = rule.get("severity", "WARN")
    if not left_key or not right_key:
        return [], set(), set()
    if left_key not in df_left.columns or right_key not in df_right.columns:
        return [], set(), set()
    left_values = set(df_left[left_key].drop_nulls().to_list())
    right_values = set(df_right[right_key].drop_nulls().to_list())
    left_missing = left_values - right_values
    right_missing = right_values - left_values
    issues: list[Issue] = []
    for value in list(left_missing)[:5000]:
        issues.append(
            Issue(
                run_id=run_id,
                issue_id=f"missing_right_{value}",
                severity=severity,
                issue_type="MISSING_IN_RIGHT",
                message="Key missing from right file",
                file_side="LEFT",
                record_key=str(value),
            )
        )
    for value in list(right_missing)[:5000]:
        issues.append(
            Issue(
                run_id=run_id,
                issue_id=f"missing_left_{value}",
                severity=severity,
                issue_type="MISSING_IN_LEFT",
                message="Key missing from left file",
                file_side="RIGHT",
                record_key=str(value),
            )
        )
    return issues, set(), set()

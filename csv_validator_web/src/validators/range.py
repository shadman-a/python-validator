from __future__ import annotations

from ..core.models import Issue


def run(df_left, df_right, rule: dict, run_id: str, mode: str):
    column = rule.get("column")
    severity = rule.get("severity", "WARN")
    min_value = rule.get("min")
    max_value = rule.get("max")
    if not column or column not in df_left.columns:
        return [], set(), set()
    series = df_left[column].cast(float, strict=False)
    issues: list[Issue] = []
    bad_rows: set[int] = set()
    for row_idx, value in enumerate(series.to_list()):
        if value is None:
            continue
        if min_value is not None and value < min_value:
            bad = True
        elif max_value is not None and value > max_value:
            bad = True
        else:
            bad = False
        if not bad:
            continue
        if len(issues) >= 5000:
            break
        issues.append(
            Issue(
                run_id=run_id,
                issue_id=f"range_{column}_{row_idx}",
                severity=severity,
                issue_type="OUT_OF_RANGE",
                message=f"Value out of range in {column}",
                file_side="SINGLE" if mode == "single" else "LEFT",
                row_index=row_idx,
                column=column,
                left_value=str(value),
            )
        )
        bad_rows.add(row_idx)
    return issues, bad_rows, set()

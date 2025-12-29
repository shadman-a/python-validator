from __future__ import annotations

import polars as pl

from ..core.models import Issue
from ..core.normalize import apply_pipeline


def _apply_value_map(value: str | None, value_map: dict | None) -> str | None:
    if value_map and value is not None:
        return value_map.get(value, value)
    return value


def run(df_left, df_right, rule: dict, run_id: str, mode: str, mapping: dict | None = None):
    if mode != "compare" or not mapping:
        return [], set(), set()
    fields = rule.get("fields", [])
    ignore_if_both_blank = rule.get("ignore_if_both_blank", False)
    severity = rule.get("severity", "WARN")
    keys = mapping.get("keys", {})
    left_key = keys.get("left")
    right_key = keys.get("right")
    if not left_key or not right_key:
        return [], set(), set()
    if left_key not in df_left.columns or right_key not in df_right.columns:
        return [], set(), set()

    left_df = df_left.select([left_key] + [mapping["fields"][field]["left"] for field in fields if field in mapping.get("fields", {})])
    right_df = df_right.select([right_key] + [mapping["fields"][field]["right"] for field in fields if field in mapping.get("fields", {})])
    joined = left_df.join(right_df, left_on=left_key, right_on=right_key, how="inner", suffix="_right")

    issues: list[Issue] = []
    bad_left: set[int] = set()
    bad_right: set[int] = set()

    for field in fields:
        field_map = mapping.get("fields", {}).get(field)
        if not field_map:
            continue
        left_col = field_map.get("left")
        right_col = field_map.get("right")
        if left_col not in joined.columns or f"{right_col}_right" not in joined.columns:
            continue
        normalize_steps = field_map.get("normalize", [])
        value_map = field_map.get("value_map")
        tolerance = field_map.get("tolerance")
        left_series = joined[left_col].cast(str).fill_null("")
        right_series = joined[f"{right_col}_right"].cast(str).fill_null("")
        for row_idx, (left_val, right_val) in enumerate(zip(left_series.to_list(), right_series.to_list())):
            left_norm = apply_pipeline(left_val, normalize_steps)
            right_norm = apply_pipeline(right_val, normalize_steps)
            left_norm = _apply_value_map(left_norm, value_map)
            right_norm = _apply_value_map(right_norm, value_map)
            if ignore_if_both_blank and not left_norm and not right_norm:
                continue
            equal = left_norm == right_norm
            if not equal and tolerance is not None:
                try:
                    equal = abs(float(left_norm) - float(right_norm)) <= float(tolerance)
                except (TypeError, ValueError):
                    equal = False
            if equal:
                continue
            if len(issues) >= 5000:
                break
            issues.append(
                Issue(
                    run_id=run_id,
                    issue_id=f"compare_{field}_{row_idx}",
                    severity=severity,
                    issue_type="MISMATCH_FIELD",
                    message=f"Field mismatch for {field}",
                    file_side="BOTH",
                    row_index=row_idx,
                    column=field,
                    left_value=left_norm,
                    right_value=right_norm,
                )
            )
            bad_left.add(row_idx)
            bad_right.add(row_idx)
    return issues, bad_left, bad_right

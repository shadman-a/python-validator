from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl
import yaml

from .html_report import write_html_report
from .io import read_csv
from .issue_writer import write_issues
from .models import Issue, RunSummary
from .utils import ensure_dir, generate_run_id, write_json
from ..validators import (
    allowed_values,
    compare_fields,
    cross_file_match,
    range as range_validator,
    regex,
    required_columns,
    required_non_null,
    row_rules,
    type_checks,
    unique_key,
)

VALIDATOR_MAP = {
    "required_columns": required_columns,
    "required_non_null": required_non_null,
    "unique_key": unique_key,
    "allowed_values": allowed_values,
    "regex": regex,
    "type_checks": type_checks,
    "range": range_validator,
    "row_rules": row_rules,
    "cross_file_match": cross_file_match,
    "compare_fields": compare_fields,
}


class RunResult:
    def __init__(self, run_id: str, run_dir: Path, summary: RunSummary, issues: list[Issue]):
        self.run_id = run_id
        self.run_dir = run_dir
        self.summary = summary
        self.issues = issues


def run_validation(
    mode: str,
    left_path: Path,
    right_path: Path | None,
    rules: dict[str, Any],
    mapping: dict[str, Any] | None,
    runs_dir: Path,
) -> RunResult:
    run_id = generate_run_id()
    run_dir = ensure_dir(runs_dir / run_id)
    logs_path = run_dir / "logs.txt"
    logs_path.write_text("Starting run\n")

    inputs_payload = {
        "mode": mode,
        "left_path": str(left_path),
        "right_path": str(right_path) if right_path else None,
        "started_at": datetime.now().isoformat(),
    }
    write_json(run_dir / "inputs.json", inputs_payload)

    (run_dir / "rules_used.yaml").write_text(yaml.safe_dump(rules, sort_keys=False))
    if mapping:
        (run_dir / "mapping_used.yaml").write_text(yaml.safe_dump(mapping, sort_keys=False))

    df_left = read_csv(left_path)
    df_right = read_csv(right_path) if right_path else None

    issues: list[Issue] = []
    bad_left: set[int] = set()
    bad_right: set[int] = set()

    validators = rules.get("validators", [])
    for rule in validators:
        validator_type = rule.get("type")
        handler = VALIDATOR_MAP.get(validator_type)
        if not handler:
            continue
        if validator_type == "compare_fields":
            new_issues, bad_left_new, bad_right_new = handler.run(
                df_left, df_right, rule, run_id, mode, mapping
            )
        else:
            new_issues, bad_left_new, bad_right_new = handler.run(
                df_left, df_right, rule, run_id, mode
            )
        issues.extend(new_issues)
        bad_left |= bad_left_new
        bad_right |= bad_right_new

    write_issues(run_dir / "issues.csv", issues)

    if mode == "compare" and df_right is not None:
        if bad_left:
            df_left.filter(pl.arange(0, df_left.height).is_in(list(bad_left))).write_csv(
                run_dir / "bad_rows_left.csv"
            )
        if bad_right:
            df_right.filter(pl.arange(0, df_right.height).is_in(list(bad_right))).write_csv(
                run_dir / "bad_rows_right.csv"
            )
    else:
        if bad_left:
            df_left.filter(pl.arange(0, df_left.height).is_in(list(bad_left))).write_csv(
                run_dir / "bad_rows.csv"
            )

    summary = RunSummary(
        run_id=run_id,
        mode=mode,
        started_at=datetime.now(),
        total_rows_left=df_left.height,
        total_rows_right=df_right.height if df_right is not None else 0,
        errors=sum(1 for issue in issues if issue.severity == "ERROR"),
        warnings=sum(1 for issue in issues if issue.severity == "WARN"),
        infos=sum(1 for issue in issues if issue.severity == "INFO"),
    )

    report = {
        "run_id": summary.run_id,
        "mode": summary.mode,
        "rows_left": summary.total_rows_left,
        "rows_right": summary.total_rows_right,
        "errors": summary.errors,
        "warnings": summary.warnings,
        "infos": summary.infos,
    }
    write_json(run_dir / "report.json", report)
    (run_dir / "summary.txt").write_text(json.dumps(report, indent=2))
    write_html_report(run_dir / "report.html", report)

    return RunResult(run_id=run_id, run_dir=run_dir, summary=summary, issues=issues)

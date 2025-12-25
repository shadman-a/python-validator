from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .models import Issue


COLUMNS = [
    "run_id",
    "severity",
    "issue_type",
    "file_side",
    "record_key",
    "row_index",
    "column",
    "left_value",
    "right_value",
    "message",
    "suggested_fix",
    "tags",
]


def write_issues(path: Path, issues: Iterable[Issue]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for issue in issues:
            writer.writerow(issue.to_row())

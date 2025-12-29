from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

Severity = Literal["INFO", "WARN", "ERROR"]
FileSide = Literal["SINGLE", "LEFT", "RIGHT", "BOTH"]


@dataclass
class Issue:
    run_id: str
    issue_id: str
    severity: Severity
    issue_type: str
    message: str
    file_side: FileSide = "SINGLE"
    row_index: int | None = None
    record_key: str | None = None
    column: str | None = None
    left_value: str | None = None
    right_value: str | None = None
    suggested_fix: str | None = None
    tags: list[str] | None = None

    def to_row(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "severity": self.severity,
            "issue_type": self.issue_type,
            "file_side": self.file_side,
            "record_key": self.record_key,
            "row_index": self.row_index,
            "column": self.column,
            "left_value": self.left_value,
            "right_value": self.right_value,
            "message": self.message,
            "suggested_fix": self.suggested_fix,
            "tags": ";".join(self.tags or []),
        }


@dataclass
class RunSummary:
    run_id: str
    mode: str
    started_at: datetime
    total_rows_left: int = 0
    total_rows_right: int = 0
    errors: int = 0
    warnings: int = 0
    infos: int = 0


@dataclass
class MappingSuggestion:
    left_column: str
    best_right: str | None
    confidence: int
    reasons: list[str]
    alternates: list[tuple[str, int, list[str]]] = field(default_factory=list)

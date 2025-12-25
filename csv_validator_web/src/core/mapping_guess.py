from __future__ import annotations

from collections import Counter
from typing import Iterable

from rapidfuzz import fuzz

from .models import MappingSuggestion
from .normalize import digits_only


def _norm_header(name: str) -> str:
    return "".join(ch.lower() for ch in name if ch.isalnum())


def _detect_type(values: Iterable[str]) -> str:
    sample = list(values)[:200]
    if not sample:
        return "text"
    numeric = sum(v.replace(".", "", 1).isdigit() for v in sample)
    emails = sum("@" in v for v in sample)
    phones = sum(len(digits_only(v) or "") >= 10 for v in sample)
    dates = sum("/" in v or "-" in v for v in sample)
    best = max(
        [(numeric, "numeric"), (emails, "email"), (phones, "phone"), (dates, "date")],
        key=lambda item: item[0],
    )
    return best[1] if best[0] > 0 else "text"


def _overlap(values_left: list[str], values_right: list[str]) -> float:
    left = {v.strip().lower() for v in values_left if v}
    right = {v.strip().lower() for v in values_right if v}
    if not left or not right:
        return 0.0
    return len(left & right) / max(len(left), 1)


def guess_mappings(
    left_columns: list[str],
    right_columns: list[str],
    left_samples: dict[str, list[str]],
    right_samples: dict[str, list[str]],
) -> list[MappingSuggestion]:
    suggestions: list[MappingSuggestion] = []
    right_norm = {col: _norm_header(col) for col in right_columns}
    right_types = {col: _detect_type(right_samples.get(col, [])) for col in right_columns}

    for left in left_columns:
        left_norm = _norm_header(left)
        left_type = _detect_type(left_samples.get(left, []))
        scored: list[tuple[str, int, list[str]]] = []
        for right in right_columns:
            reasons = []
            header_score = 100 if left_norm == right_norm[right] else fuzz.ratio(left_norm, right_norm[right])
            if header_score:
                reasons.append(f"header fuzzy {header_score}")
            type_score = 15 if left_type == right_types[right] else 0
            if type_score:
                reasons.append(f"type {left_type}")
            overlap_score = int(_overlap(left_samples.get(left, []), right_samples.get(right, [])) * 100)
            if overlap_score:
                reasons.append(f"overlap {overlap_score}%")
            confidence = min(100, int(header_score * 0.6 + type_score + overlap_score * 0.4))
            scored.append((right, confidence, reasons))
        scored.sort(key=lambda item: item[1], reverse=True)
        best = scored[0] if scored else (None, 0, [])
        alternates = scored[1:3] if len(scored) > 1 else []
        suggestions.append(
            MappingSuggestion(
                left_column=left,
                best_right=best[0],
                confidence=best[1],
                reasons=best[2],
                alternates=alternates,
            )
        )
    return suggestions

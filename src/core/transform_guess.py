from __future__ import annotations

from collections import Counter
import re
from typing import Iterable

from rapidfuzz import fuzz

from .normalize import apply_pipeline, digits_only


YES_TOKENS = {"y", "yes", "true", "t", "1", "on"}
NO_TOKENS = {"n", "no", "false", "f", "0", "off"}


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


def _needs_trim(values: Iterable[str]) -> bool:
    return any(v != v.strip() for v in values if v)


def _needs_collapse(values: Iterable[str]) -> bool:
    return any(re.search(r"\s{2,}", v or "") for v in values)


def _normalize_values(values: Iterable[str], steps: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        if value is None:
            continue
        output = apply_pipeline(str(value), steps)
        if output is None:
            continue
        output = str(output)
        if output:
            normalized.append(output)
    return normalized


def _unique(values: Iterable[str], limit: int = 30) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value is None:
            continue
        value = str(value)
        if not value:
            continue
        if value not in seen:
            seen.append(value)
        if len(seen) >= limit:
            break
    return seen


def _yes_no_map(values: list[str]) -> dict[str, str] | None:
    tokens = {v.strip().lower() for v in values if v and v.strip()}
    if not tokens:
        return None
    if not tokens <= (YES_TOKENS | NO_TOKENS):
        return None
    if not (tokens & YES_TOKENS and tokens & NO_TOKENS):
        return None
    if tokens & {"true", "false", "t", "f"}:
        yes_value, no_value = "True", "False"
    else:
        yes_value, no_value = "Yes", "No"
    mapping: dict[str, str] = {}
    for raw in values:
        if not raw:
            continue
        token = raw.strip().lower()
        if token in YES_TOKENS:
            mapping[raw] = yes_value
        elif token in NO_TOKENS:
            mapping[raw] = no_value
    mapping = {key: value for key, value in mapping.items() if key != value}
    return mapping or None


def _best_match(value: str, candidates: set[str]) -> tuple[str | None, int]:
    if not candidates:
        return None, 0
    normalized = re.sub(r"[^a-z0-9]", "", value.lower())
    best_candidate = None
    best_score = 0
    for candidate in candidates:
        cand_norm = re.sub(r"[^a-z0-9]", "", candidate.lower())
        score = fuzz.ratio(normalized, cand_norm)
        if score > best_score:
            best_score = score
            best_candidate = candidate
    return best_candidate, best_score


def _choose_canonical(left: str, right: str, counts: Counter[str]) -> str:
    if counts[left] > counts[right]:
        return left
    if counts[right] > counts[left]:
        return right
    if len(right) > len(left):
        return right
    return left


def _suggest_value_map(
    left_values: list[str],
    right_values: list[str],
    normalize_steps: list[str],
) -> tuple[dict[str, str] | None, str | None]:
    left_norm = _unique(_normalize_values(left_values, normalize_steps), limit=30)
    right_norm = _unique(_normalize_values(right_values, normalize_steps), limit=30)
    if not left_norm or not right_norm:
        return None, None
    if len(left_norm) > 15 or len(right_norm) > 15:
        return None, None

    combined = left_norm + right_norm
    yes_no = _yes_no_map(combined)
    if yes_no:
        return yes_no, "Yes/No-style values detected"

    left_set = set(left_norm)
    right_set = set(right_norm)
    if left_set == right_set:
        return None, None

    counts = Counter(combined)
    mapping: dict[str, str] = {}

    for value in left_set - right_set:
        match, score = _best_match(value, right_set)
        if match and score >= 92:
            canonical = _choose_canonical(value, match, counts)
            if value != canonical:
                mapping[value] = canonical

    for value in right_set - left_set:
        match, score = _best_match(value, left_set)
        if match and score >= 92:
            canonical = _choose_canonical(match, value, counts)
            if value != canonical and value not in mapping:
                mapping[value] = canonical

    if not mapping or len(mapping) > 12:
        return None, None
    return mapping, "Small categorical set with close matches"


def guess_transformations(
    mapping_fields: dict[str, dict],
    left_samples: dict[str, list[str]],
    right_samples: dict[str, list[str]],
) -> dict[str, dict]:
    suggestions: dict[str, dict] = {}
    for field, config in mapping_fields.items():
        left_col = config.get("left") or ""
        right_col = config.get("right") or ""
        left_values = left_samples.get(left_col, [])
        right_values = right_samples.get(right_col, [])
        combined = left_values + right_values
        normalize_steps: list[str] = []
        reasons: list[str] = []

        if _needs_trim(combined):
            normalize_steps.append("trim")
            reasons.append("Trim whitespace")
        if _needs_collapse(combined):
            normalize_steps.append("collapse_whitespace")
            reasons.append("Collapse repeated spaces")

        detected = _detect_type(combined)
        if detected == "email":
            normalize_steps.append("normalize_email")
            reasons.append("Email-like values")
        elif detected == "phone":
            normalize_steps.append("normalize_phone_us")
            reasons.append("Phone-like values")

        value_map, value_reason = _suggest_value_map(left_values, right_values, normalize_steps)
        if value_map and value_reason:
            reasons.append(value_reason)

        if normalize_steps or value_map:
            suggestions[field] = {
                "normalize": normalize_steps,
                "value_map": value_map,
                "reasons": reasons,
            }
    return suggestions

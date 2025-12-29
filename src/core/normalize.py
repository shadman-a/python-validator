from __future__ import annotations

import re
from typing import Callable

NormalizationFn = Callable[[str | None], str | None]


SUFFIXES = {"jr", "sr", "ii", "iii"}


def _coerce(value: str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def trim(value: str | None) -> str | None:
    value = _coerce(value)
    return value.strip() if value is not None else None


def lower(value: str | None) -> str | None:
    value = trim(value)
    return value.lower() if value is not None else None


def upper(value: str | None) -> str | None:
    value = trim(value)
    return value.upper() if value is not None else None


def collapse_whitespace(value: str | None) -> str | None:
    value = trim(value)
    if value is None:
        return None
    return re.sub(r"\s+", " ", value)


def remove_punctuation(value: str | None) -> str | None:
    value = trim(value)
    if value is None:
        return None
    return re.sub(r"[^\w\s]", "", value)


def digits_only(value: str | None) -> str | None:
    value = _coerce(value)
    if value is None:
        return None
    digits = re.sub(r"\D", "", value)
    return digits or None


def null_if_blank(value: str | None) -> str | None:
    value = trim(value)
    if value is None:
        return None
    return value if value else None


def normalize_email(value: str | None) -> str | None:
    value = lower(value)
    return value


def normalize_phone_us(value: str | None) -> str | None:
    value = digits_only(value)
    if value is None:
        return None
    if len(value) == 11 and value.startswith("1"):
        value = value[1:]
    return value if len(value) == 10 else value


def remove_suffixes(value: str | None) -> str | None:
    value = collapse_whitespace(value)
    if value is None:
        return None
    parts = value.split()
    if parts and parts[-1].lower().strip(".") in SUFFIXES:
        parts = parts[:-1]
    return " ".join(parts) if parts else None


NORMALIZERS: dict[str, NormalizationFn] = {
    "trim": trim,
    "lower": lower,
    "upper": upper,
    "collapse_whitespace": collapse_whitespace,
    "remove_punctuation": remove_punctuation,
    "digits_only": digits_only,
    "null_if_blank": null_if_blank,
    "normalize_email": normalize_email,
    "normalize_phone_us": normalize_phone_us,
    "remove_suffixes": remove_suffixes,
}


def apply_pipeline(value: str | None, steps: list[str]) -> str | None:
    result = value
    for step in steps:
        fn = NORMALIZERS.get(step)
        if fn:
            result = fn(result)
    return result

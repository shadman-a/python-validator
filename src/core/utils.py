from __future__ import annotations

import json
import os
import secrets
from datetime import datetime
from pathlib import Path


def generate_run_id() -> str:
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    token = secrets.token_hex(3)
    return f"{stamp}_{token}"


def safe_int(value: str | None, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str))


def is_subpath(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def sanitize_filename(name: str) -> str:
    keep = [c for c in name if c.isalnum() or c in ("-", "_", ".")]
    return "".join(keep) or "mapping"


def human_bool(value: str | None) -> bool:
    return (value or "").lower() in {"1", "true", "yes", "on"}


def format_timestamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def env_int(name: str, default: int) -> int:
    return safe_int(os.getenv(name), default)

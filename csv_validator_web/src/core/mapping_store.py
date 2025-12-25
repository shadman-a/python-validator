from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .utils import sanitize_filename


def load_mapping(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text()) if path.exists() else {}


def save_mapping(base_dir: Path, name: str, payload: dict[str, Any]) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    filename = sanitize_filename(name)
    if not filename.endswith(".yaml"):
        filename = f"{filename}.yaml"
    path = base_dir / filename
    path.write_text(yaml.safe_dump(payload, sort_keys=False))
    return path

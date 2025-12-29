from __future__ import annotations

from pathlib import Path

import polars as pl


def read_csv(path: Path) -> pl.DataFrame:
    return pl.read_csv(path, infer_schema_length=500, try_parse_dates=True)


def sample_values(df: pl.DataFrame, limit: int = 2000) -> dict[str, list[str]]:
    sample = df.head(limit)
    samples: dict[str, list[str]] = {}
    for col in sample.columns:
        values = sample.get_column(col).to_list()
        samples[col] = [str(v) for v in values if v is not None][:limit]
    return samples

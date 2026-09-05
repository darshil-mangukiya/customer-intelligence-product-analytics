from __future__ import annotations

import shutil
import tempfile
from itertools import zip_longest
from pathlib import Path

import pandas as pd


def write_csv(df: pd.DataFrame, path: Path, index: bool = False) -> Path:
    """Write a dataframe with consistent parent directory creation."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.SpooledTemporaryFile(
        mode="w+", encoding="utf-8", newline="", max_size=8 * 1024 * 1024
    ) as buffer:
        df.to_csv(buffer, index=index)
        buffer.seek(0)
        if path.exists():
            with path.open(encoding="utf-8", newline="") as existing:
                existing_chunks = iter(lambda: existing.read(1024 * 1024), "")
                buffer_chunks = iter(lambda: buffer.read(1024 * 1024), "")
                if all(left == right for left, right in zip_longest(existing_chunks, buffer_chunks)):
                    return path
            buffer.seek(0)
        with path.open("w", encoding="utf-8", newline="") as destination:
            shutil.copyfileobj(buffer, destination)
    return path


def read_csv(path: Path, parse_dates: list[str] | None = None) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=parse_dates)


def write_markdown(lines: list[str], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines).strip() + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8")
    return path


def money(value: float) -> str:
    return f"${value:,.0f}"


def pct(value: float) -> str:
    return f"{value:.1%}"

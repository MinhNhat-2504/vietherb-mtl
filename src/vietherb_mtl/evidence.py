"""Lightweight helpers shared by evidence generation and its unit tests."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


def sha256(path: Path) -> str:
    """Hash binary files byte-for-byte and normalize newlines in UTF-8 text."""

    payload = path.read_bytes()
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        pass
    else:
        if "\x00" not in text:
            payload = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class RunFiles:
    metrics: Path
    predictions: Path
    manifest: Path

    @property
    def inputs(self) -> tuple[Path, Path, Path]:
        return self.metrics, self.predictions, self.manifest


def archived_run(path: Path, prefix: str) -> RunFiles:
    """Resolve one run from the flat release archive naming convention."""

    return RunFiles(
        metrics=path / f"{prefix}_metrics.csv",
        predictions=path / f"{prefix}_predictions.parquet",
        manifest=path / f"{prefix}_run_manifest.json",
    )

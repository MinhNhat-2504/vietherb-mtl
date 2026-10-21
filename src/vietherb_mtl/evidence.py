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


@dataclass(frozen=True)
class ArtifactVerification:
    missing: tuple[str, ...]
    unexpected: tuple[str, ...]
    mismatched: tuple[str, ...]
    tolerated_pdf_variance: tuple[str, ...]
    exact_matches: int

    @property
    def passed(self) -> bool:
        return not (self.missing or self.unexpected or self.mismatched)


def valid_pdf(path: Path) -> bool:
    """Apply a small integrity check without adding a PDF parser dependency."""

    if not path.is_file() or path.stat().st_size < 8:
        return False
    with path.open("rb") as handle:
        header = handle.read(5)
        handle.seek(max(0, path.stat().st_size - 1024))
        trailer = handle.read()
    return header == b"%PDF-" and b"%%EOF" in trailer


def verify_artifact_hashes(
    expected: dict[str, str],
    actual: dict[str, str],
    artifact_root: Path,
    allow_pdf_renderer_variance: bool = False,
) -> ArtifactVerification:
    """Compare evidence hashes, optionally tolerating non-semantic PDF bytes.

    A PDF mismatch is tolerated only when its separately rendered PNG companion
    is present and byte-exact, and the regenerated PDF has a valid header and
    trailer. Tables and PNG previews always remain exact hash gates.
    """

    missing = tuple(sorted(set(expected) - set(actual)))
    unexpected = tuple(sorted(set(actual) - set(expected)))
    raw_mismatches = sorted(
        path for path in set(expected) & set(actual) if expected[path] != actual[path]
    )
    tolerated = []
    mismatched = []
    for relative_path in raw_mismatches:
        png_companion = str(Path(relative_path).with_suffix(".png")).replace("\\", "/")
        may_tolerate = (
            allow_pdf_renderer_variance
            and relative_path.endswith(".pdf")
            and png_companion in expected
            and png_companion in actual
            and expected[png_companion] == actual[png_companion]
            and valid_pdf(artifact_root / relative_path)
        )
        (tolerated if may_tolerate else mismatched).append(relative_path)
    return ArtifactVerification(
        missing=missing,
        unexpected=unexpected,
        mismatched=tuple(mismatched),
        tolerated_pdf_variance=tuple(tolerated),
        exact_matches=len(set(expected) & set(actual)) - len(raw_mismatches),
    )

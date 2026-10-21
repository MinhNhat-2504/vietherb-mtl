"""Lightweight helpers shared by evidence generation and its unit tests."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


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
    tolerated_png_variance: tuple[str, ...]
    png_mean_absolute_error: dict[str, float]
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


def normalized_image_mae(reference: Path, candidate: Path) -> float | None:
    """Return normalized RGB mean absolute error, or None for incompatible images."""

    try:
        with Image.open(reference) as reference_image, Image.open(candidate) as candidate_image:
            if reference_image.size != candidate_image.size:
                return None
            reference_rgb = reference_image.convert("RGB")
            candidate_rgb = candidate_image.convert("RGB")
            channel_means = ImageStat.Stat(
                ImageChops.difference(reference_rgb, candidate_rgb)
            ).mean
    except (OSError, ValueError):
        return None
    return float(sum(channel_means) / (len(channel_means) * 255.0))


def verify_artifact_hashes(
    expected: dict[str, str],
    actual: dict[str, str],
    reference_root: Path,
    artifact_root: Path,
    allow_renderer_variance: bool = False,
    maximum_png_mae: float = 0.02,
) -> ArtifactVerification:
    """Compare evidence hashes, optionally tolerating bounded renderer variance.

    Cross-platform PNG differences must preserve dimensions and remain under a
    normalized pixel-MAE threshold. A PDF mismatch is tolerated only when its
    PNG companion is exact or within that threshold and the PDF is structurally
    valid. Non-image artifacts always remain byte-exact gates.
    """

    missing = tuple(sorted(set(expected) - set(actual)))
    unexpected = tuple(sorted(set(actual) - set(expected)))
    raw_mismatches = sorted(
        path for path in set(expected) & set(actual) if expected[path] != actual[path]
    )
    tolerated_pdf = []
    tolerated_png = []
    png_errors: dict[str, float] = {}
    mismatched = []
    for relative_path in (path for path in raw_mismatches if path.endswith(".png")):
        error = normalized_image_mae(
            reference_root / relative_path,
            artifact_root / relative_path,
        )
        if error is not None:
            png_errors[relative_path] = error
        if allow_renderer_variance and error is not None and error <= maximum_png_mae:
            tolerated_png.append(relative_path)
        else:
            mismatched.append(relative_path)
    for relative_path in (path for path in raw_mismatches if not path.endswith(".png")):
        png_companion = str(Path(relative_path).with_suffix(".png")).replace("\\", "/")
        companion_acceptable = (
            png_companion in expected
            and png_companion in actual
            and (
                expected[png_companion] == actual[png_companion]
                or png_companion in tolerated_png
            )
        )
        may_tolerate = (
            allow_renderer_variance
            and relative_path.endswith(".pdf")
            and companion_acceptable
            and valid_pdf(artifact_root / relative_path)
        )
        (tolerated_pdf if may_tolerate else mismatched).append(relative_path)
    return ArtifactVerification(
        missing=missing,
        unexpected=unexpected,
        mismatched=tuple(sorted(mismatched)),
        tolerated_pdf_variance=tuple(tolerated_pdf),
        tolerated_png_variance=tuple(tolerated_png),
        png_mean_absolute_error=png_errors,
        exact_matches=len(set(expected) & set(actual)) - len(raw_mismatches),
    )

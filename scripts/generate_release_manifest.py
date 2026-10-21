#!/usr/bin/env python
"""Hash the compact, redistributable publication bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT_FILES = (
    Path(".zenodo.json"),
    Path("CITATION.cff"),
    Path("LICENSE"),
    Path("README.md"),
    Path("pyproject.toml"),
)
TREE_ROOTS = (
    Path("configs"),
    Path("src"),
    Path("scripts"),
    Path("tests"),
    Path("docs/evidence"),
    Path("docs/manifests"),
)
DOC_FILES = (
    Path("docs/cover_letter.md"),
    Path("docs/environment_manifest.json"),
    Path("docs/experiment_protocol.md"),
    Path("docs/project_status.md"),
    Path("docs/submission_checklist.md"),
    Path("docs/submission_roadmap.md"),
    Path("docs/zenodo_release_checklist.md"),
    Path("paper/README.md"),
    Path("paper/main.tex"),
    Path("paper/main.pdf"),
    Path("paper/references.bib"),
    Path("paper/supplement.tex"),
    Path("paper/supplement.pdf"),
)
EXCLUDED_SUFFIXES = {".aux", ".bbl", ".blg", ".log", ".out", ".pyc"}


def hash_payload(path: Path, mode: str | None = None) -> tuple[bytes, str]:
    """Return a cross-platform payload and the hashing mode used for it.

    Git checkouts on Windows can contain CRLF while GitHub/Zenodo source
    archives contain LF for the same tracked text blob. UTF-8 text is therefore
    newline-normalized before hashing. Binary publication artifacts retain an
    exact byte hash.
    """

    payload = path.read_bytes()
    if mode == "raw":
        return payload, mode
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        if mode == "utf8_lf":
            raise ValueError(f"Expected UTF-8 text artifact: {path}") from None
        return payload, "raw"
    if "\x00" in text:
        if mode == "utf8_lf":
            raise ValueError(f"Expected UTF-8 text artifact without NUL bytes: {path}")
        return payload, "raw"
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return normalized, "utf8_lf"


def sha256(path: Path, mode: str | None = None) -> tuple[str, str]:
    payload, resolved_mode = hash_payload(path, mode)
    return hashlib.sha256(payload).hexdigest(), resolved_mode


def collect(root: Path) -> list[Path]:
    candidates = [root / path for path in (*ROOT_FILES, *DOC_FILES)]
    for tree_root in TREE_ROOTS:
        candidates.extend((root / tree_root).rglob("*"))
    return sorted(
        {
            path.resolve()
            for path in candidates
            if path.is_file()
            and path.suffix.lower() not in EXCLUDED_SUFFIXES
            and "__pycache__" not in path.parts
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path, default=Path("docs/release_manifest.json"))
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    out = args.out if args.out.is_absolute() else root / args.out
    if args.verify:
        payload = json.loads(out.read_text(encoding="utf-8"))
        failures = []
        for relative_path, expected in payload["artifacts"].items():
            path = root / relative_path
            if not path.is_file():
                failures.append(relative_path)
                continue
            digest, _ = sha256(path, expected.get("hash_mode", "raw"))
            if digest != expected["sha256"]:
                failures.append(relative_path)
        if failures:
            raise SystemExit(f"Release verification failed: {failures}")
        print(f"Verified {len(payload['artifacts'])} release artifacts")
        return

    files = [path for path in collect(root) if path != out.resolve()]
    artifacts = {}
    for path in files:
        digest, hash_mode = sha256(path)
        artifacts[path.relative_to(root).as_posix()] = {
            "bytes": path.stat().st_size,
            "sha256": digest,
            "hash_mode": hash_mode,
        }
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "release": "v0.1.0",
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out} with {len(artifacts)} artifacts")


if __name__ == "__main__":
    main()

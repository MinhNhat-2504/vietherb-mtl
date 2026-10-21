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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
            if not path.is_file() or sha256(path) != expected["sha256"]:
                failures.append(relative_path)
        if failures:
            raise SystemExit(f"Release verification failed: {failures}")
        print(f"Verified {len(payload['artifacts'])} release artifacts")
        return

    files = [path for path in collect(root) if path != out.resolve()]
    artifacts = {
        path.relative_to(root).as_posix(): {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in files
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

#!/usr/bin/env python3
"""Export a frozen model table to Chemprop CSV without changing split IDs."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.out.exists() and not args.overwrite:
        raise FileExistsError(f"{args.out} exists; pass --overwrite explicitly")
    source = args.dataset_dir / "model_table.parquet"
    frame = pd.read_parquet(source)
    tasks = [column for column in frame if column.startswith("activity_")]
    required = {"molecule_id", "canonical_smiles", "component_id", "split", *tasks}
    missing = required - set(frame)
    if missing:
        raise ValueError(f"model table missing columns: {sorted(missing)}")
    exported = frame[["molecule_id", "canonical_smiles", "component_id", *tasks, "split"]].copy()
    exported["split"] = exported["split"].replace({"validation": "val"})
    if set(exported["split"]) != {"train", "val", "test"}:
        raise RuntimeError("Chemprop split column must contain exactly train/val/test")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    exported.to_csv(args.out, index=False)
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": str(source),
        "source_sha256": sha256(source),
        "dataset_manifest_sha256": sha256(args.dataset_dir / "manifest.json"),
        "rows": len(exported),
        "tasks": tasks,
        "split_counts": exported["split"].value_counts().to_dict(),
        "output_sha256": sha256(args.out),
    }
    args.out.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

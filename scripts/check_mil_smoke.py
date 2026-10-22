#!/usr/bin/env python3
"""Fail-closed acceptance check for the synthetic end-to-end MIL smoke run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

REQUIRED_FAMILIES = {"shared_primary", "naive_broadcast", "mil_aux", "permuted_mil"}


def check(output_dir: Path) -> dict[str, object]:
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    metrics = pd.read_csv(output_dir / "metrics.csv")
    families = set(metrics["family"].astype(str))
    missing = sorted(REQUIRED_FAMILIES - families)
    if missing:
        raise RuntimeError(f"MIL smoke run missing model families: {missing}")
    if not manifest.get("synthetic") or manifest.get("scientific_results"):
        raise RuntimeError("smoke manifest must be synthetic and non-scientific")
    if metrics.empty or not metrics["pr_auc"].map(pd.api.types.is_number).all():
        raise RuntimeError("smoke metrics are empty or non-numeric")
    return {
        "status": "passed",
        "synthetic": True,
        "scientific_results": False,
        "rows": int(len(metrics)),
        "families": sorted(families),
        "device": manifest.get("device"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(check(args.output_dir), indent=2))


if __name__ == "__main__":
    main()

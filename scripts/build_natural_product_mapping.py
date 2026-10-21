#!/usr/bin/env python3
"""Map ChEMBL 37's COCONUT-derived natural-product flag to standardized IDs."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from build_dataset import stable_id, standardize


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--activities", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.out.exists() and not args.overwrite:
        raise FileExistsError(f"{args.out} exists; pass --overwrite explicitly")
    frame = pd.read_parquet(
        args.activities, columns=["canonical_smiles", "natural_product"]
    )
    standardized = {}
    rejected = 0
    for smiles in frame["canonical_smiles"].dropna().unique():
        result = standardize(smiles)
        if result is None:
            rejected += 1
        else:
            standardized[smiles] = result
    frame = frame[frame["canonical_smiles"].isin(standardized)].copy()
    frame["inchikey"] = frame["canonical_smiles"].map(standardized).map(lambda item: item[1])
    frame["molecule_id"] = frame["inchikey"].map(stable_id)
    mapping = frame.groupby(["molecule_id", "inchikey"], as_index=False).agg(
        is_natural_product=("natural_product", "max")
    )
    mapping["is_natural_product"] = mapping["is_natural_product"].fillna(0).astype(bool)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    mapping.to_parquet(args.out, index=False)
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": str(args.activities),
        "source_sha256": sha256(args.activities),
        "rows": len(mapping),
        "natural_products": int(mapping["is_natural_product"].sum()),
        "rejected_unique_smiles": rejected,
        "output_sha256": sha256(args.out),
        "provenance": "ChEMBL 37 molecule_dictionary.natural_product (COCONUT 2025-07)",
    }
    args.out.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

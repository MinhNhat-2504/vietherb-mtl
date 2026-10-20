#!/usr/bin/env python3
"""Create deterministic synthetic rows for end-to-end software smoke tests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261020)
    parser.add_argument("--rows", type=int, default=360)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    rings = ["c1ccccc1", "c1ccncc1", "C1CCCCC1", "c1ncccc1", "c1ccc2ccccc2c1", "C1CCNCC1"]
    tails = ["", "C", "CC", "CCC", "O", "N", "Cl", "F", "C(=O)O", "C#N"]
    rows = []
    splits = ("train", "validation", "test")
    for index in range(args.rows):
        family = index % len(rings)
        tail = tails[(index // len(rings)) % len(tails)]
        chain = "C" * (1 + (index // (len(rings) * len(tails))) % 5)
        smiles = rings[family] + chain + tail
        latent = family * 0.45 + len(tail) * 0.12 + rng.normal(0, 0.7)
        split = splits[(index // 12) % 10 >= 7 and 1 or 0]
        if (index // 12) % 10 >= 9:
            split = "test"
        labels = {
            "activity_DPP4": float(latent + rng.normal() > 1.1),
            "activity_ACHE": float(-latent + family + rng.normal() > 1.7),
            "activity_PTGS2": float(len(tail) + rng.normal() > 2.5),
        }
        # Missing primary measurements emulate sparse ChEMBL task matrices.
        for task in list(labels):
            if rng.random() < 0.22:
                labels[task] = np.nan
        rows.append(
            {
                "molecule_id": f"DEMO_{index:05d}",
                "canonical_smiles": smiles,
                "inchikey": f"DEMO{index:023d}"[:27],
                "murcko_scaffold": rings[family],
                "component_id": f"DEMO_CC_{index:05d}",
                "split": split,
                "is_natural_product": bool(index % 3 == 0),
                **labels,
                "ethno_diabetes": float(latent + rng.normal() > 0.9),
                "ethno_neuro": float(family in {1, 5} and rng.random() > 0.25),
                "ethno_inflammation": float(len(tail) > 1 and rng.random() > 0.3),
            }
        )
    frame = pd.DataFrame(rows)
    args.out.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(args.out / "model_table.parquet", index=False)
    membership = pd.DataFrame(
        {
            "bag_id": [f"DEMO_BAG_{index // 3:05d}" for index in range(len(frame))],
            "molecule_id": frame["molecule_id"],
            "split": frame["split"],
        }
    )
    membership.to_parquet(args.out / "bag_membership.parquet", index=False)
    bags = (
        membership[["bag_id", "split"]]
        .merge(
            frame[["molecule_id", "ethno_diabetes", "ethno_neuro", "ethno_inflammation"]],
            left_index=True,
            right_index=True,
        )
        .groupby("bag_id", as_index=False)
        .agg(
            split=("split", "first"),
            ethno_diabetes=("ethno_diabetes", "max"),
            ethno_neuro=("ethno_neuro", "max"),
            ethno_inflammation=("ethno_inflammation", "max"),
        )
    )
    bags.to_parquet(args.out / "bags.parquet", index=False)
    (args.out / "manifest.json").write_text(
        json.dumps(
            {"synthetic": True, "seed": args.seed, "rows": len(frame), "no_scientific_use": True},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(frame["split"].value_counts().to_string())


if __name__ == "__main__":
    main()

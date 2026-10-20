#!/usr/bin/env python3
"""Fail closed on dataset integrity and split-leakage invariants."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


def pairwise_overlaps(values: dict[str, set[str]]) -> dict[str, int]:
    names = sorted(values)
    return {
        f"{left}__{right}": len(values[left] & values[right])
        for index, left in enumerate(names)
        for right in names[index + 1 :]
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    table_path = args.dataset_dir / "model_table.parquet"
    frame = pd.read_parquet(table_path)
    required = {
        "molecule_id",
        "inchikey",
        "murcko_scaffold",
        "component_id",
        "split",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"model table missing audit columns: {sorted(missing)}")
    if frame["molecule_id"].duplicated().any():
        raise RuntimeError("duplicate molecule_id rows found")
    expected_splits = {"train", "validation", "test"}
    observed_splits = set(frame["split"].dropna())
    if observed_splits != expected_splits:
        raise RuntimeError(f"expected splits {expected_splits}, got {observed_splits}")

    split_sets = {}
    for column in ("molecule_id", "inchikey", "murcko_scaffold", "component_id"):
        split_sets[column] = {
            split: set(frame.loc[frame["split"] == split, column].astype(str))
            for split in sorted(expected_splits)
        }
    overlaps = {column: pairwise_overlaps(values) for column, values in split_sets.items()}
    if any(value for column in overlaps.values() for value in column.values()):
        raise RuntimeError(f"split leakage detected: {overlaps}")

    activity_columns = [column for column in frame if column.startswith("activity_")]
    target_counts = {}
    for split in sorted(expected_splits):
        subset = frame[frame["split"] == split]
        target_counts[split] = {
            task: {
                "measured": int(subset[task].notna().sum()),
                "positive": int(subset[task].fillna(0).sum()),
                "negative": int((subset[task] == 0).sum()),
            }
            for task in activity_columns
        }

    bag_summary = {"bags": 0, "membership_edges": 0, "cross_split_bags": 0}
    bags_path = args.dataset_dir / "bags.parquet"
    membership_path = args.dataset_dir / "bag_membership.parquet"
    if bags_path.exists() != membership_path.exists():
        raise RuntimeError("bags.parquet and bag_membership.parquet must appear together")
    if bags_path.exists():
        bags = pd.read_parquet(bags_path)
        membership = pd.read_parquet(membership_path)
        molecule_split = frame.set_index("molecule_id")["split"]
        membership["molecule_split"] = membership["molecule_id"].map(molecule_split)
        if membership["molecule_split"].isna().any():
            raise RuntimeError("bag membership contains molecules absent from model table")
        cross_split = int((membership.groupby("bag_id")["molecule_split"].nunique() > 1).sum())
        if cross_split:
            raise RuntimeError(f"{cross_split} plant bags cross splits")
        bag_summary = {
            "bags": len(bags),
            "membership_edges": len(membership),
            "cross_split_bags": cross_split,
        }

    report = {
        "audited_at": datetime.now(UTC).isoformat(),
        "dataset": str(args.dataset_dir),
        "rows": len(frame),
        "split_counts": frame["split"].value_counts().to_dict(),
        "unique_scaffolds": int(frame["murcko_scaffold"].nunique()),
        "overlaps": overlaps,
        "targets": target_counts,
        "bags": bag_summary,
        "passed": True,
    }
    output = args.out or (args.dataset_dir / "audit.json")
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

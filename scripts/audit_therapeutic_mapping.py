#!/usr/bin/env python3
"""Audit the locked VietHerb therapeutic-use annotation table.

The table is intentionally usable before the authorized export arrives.  An
empty table produces a machine-readable ``pending`` report rather than
inventing labels.  Once two reviewers have labelled the fixed sample, the
same command reports agreement and a bootstrap interval for Cohen's kappa.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

REQUIRED_COLUMNS = {
    "raw_use_normalized",
    "term_id",
    "term_label",
    "ontology",
    "auxiliary_task",
    "mapping_method",
    "mapping_confidence",
    "reviewer_1",
    "reviewer_2",
    "adjudicated",
    "notes",
}
VALID_TASKS = {"ethno_diabetes", "ethno_neuro", "ethno_inflammation"}


def _labels(values: pd.Series) -> pd.Series:
    return values.fillna("").astype(str).str.strip().str.casefold()


def stratified_sample(frame: pd.DataFrame, size: int, seed: int) -> pd.DataFrame:
    """Draw a deterministic sample stratified by task and confidence band."""

    if size <= 0 or len(frame) <= size:
        return frame.copy()
    confidence = pd.to_numeric(frame["mapping_confidence"], errors="coerce").fillna(0.0)
    bands = pd.cut(
        confidence,
        bins=[-np.inf, 0.5, 0.8, np.inf],
        labels=["low", "medium", "high"],
    ).astype(str)
    grouped = frame.assign(_confidence_band=bands).groupby(
        ["auxiliary_task", "_confidence_band"], sort=True, observed=True
    )
    rng = np.random.default_rng(seed)
    selected: list[int] = []
    for _, group in grouped:
        quota = max(1, round(size * len(group) / len(frame)))
        quota = min(quota, len(group))
        selected.extend(rng.choice(group.index.to_numpy(), size=quota, replace=False).tolist())
    if len(selected) > size:
        selected = rng.choice(np.asarray(selected), size=size, replace=False).tolist()
    elif len(selected) < size:
        remaining = frame.index.difference(selected)
        extra = rng.choice(remaining.to_numpy(), size=size - len(selected), replace=False)
        selected.extend(extra.tolist())
    return frame.loc[sorted(selected)].copy()


def bootstrap_kappa(left: np.ndarray, right: np.ndarray, seed: int, replicates: int) -> list[float]:
    rng = np.random.default_rng(seed)
    values: list[float] = []
    for _ in range(replicates):
        indices = rng.integers(0, len(left), size=len(left))
        if len(np.unique(left[indices])) < 2 and len(np.unique(right[indices])) < 2:
            continue
        value = cohen_kappa_score(left[indices], right[indices])
        if np.isfinite(value):
            values.append(float(value))
    return values


def audit(frame: pd.DataFrame, sample_size: int, seed: int, bootstrap_replicates: int) -> dict:
    if not REQUIRED_COLUMNS.issubset(frame.columns):
        missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
        raise ValueError(f"mapping table missing columns: {missing}")
    confidence = pd.to_numeric(frame["mapping_confidence"], errors="coerce")
    invalid_confidence = int((confidence.notna() & ~confidence.between(0, 1)).sum())
    invalid_tasks = sorted(set(frame["auxiliary_task"].dropna()) - VALID_TASKS)
    sample = stratified_sample(frame, sample_size, seed)
    left = _labels(sample["reviewer_1"])
    right = _labels(sample["reviewer_2"])
    complete = (left.ne("") & right.ne(""))
    agreement: dict[str, object] = {
        "sample_rows": int(len(sample)),
        "complete_reviewer_pairs": int(complete.sum()),
        "exact_agreement": None,
        "cohen_kappa": None,
        "bootstrap_95_ci": None,
    }
    if complete.any():
        left_complete = left[complete].to_numpy()
        right_complete = right[complete].to_numpy()
        agreement["exact_agreement"] = float(np.mean(left_complete == right_complete))
        if len(np.unique(np.concatenate([left_complete, right_complete]))) > 1:
            kappa = float(cohen_kappa_score(left_complete, right_complete))
            agreement["cohen_kappa"] = kappa
            values = bootstrap_kappa(left_complete, right_complete, seed, bootstrap_replicates)
            if values:
                agreement["bootstrap_95_ci"] = [
                    float(np.quantile(values, 0.025)),
                    float(np.quantile(values, 0.975)),
                ]
    expected = min(sample_size, len(frame))
    if len(frame) == 0:
        status = "pending_authorized_export"
    elif agreement["complete_reviewer_pairs"] < expected:
        status = "pending_two_reviewer_labels"
    elif _labels(sample["adjudicated"]).eq("").any():
        status = "pending_adjudication"
    else:
        status = "complete"
    return {
        "kind": "therapeutic_use_mapping_audit",
        "status": status,
        "rows": int(len(frame)),
        "unique_raw_use_normalized": int(frame["raw_use_normalized"].nunique(dropna=True)),
        "invalid_confidence_rows": invalid_confidence,
        "invalid_auxiliary_tasks": invalid_tasks,
        "sample_size_requested": int(sample_size),
        "sample_seed": int(seed),
        "agreement": agreement,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sample-out", type=Path)
    parser.add_argument("--sample-size", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20261020)
    parser.add_argument("--bootstrap-replicates", type=int, default=2000)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    frame = pd.read_csv(args.input)
    report = audit(frame, args.sample_size, args.seed, args.bootstrap_replicates)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.sample_out:
        sample = stratified_sample(frame, args.sample_size, args.seed)
        args.sample_out.parent.mkdir(parents=True, exist_ok=True)
        sample.to_csv(args.sample_out, index=False)
    print(json.dumps(report, indent=2))
    if args.require_complete and report["status"] != "complete":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Summarize runs and compute a hierarchical paired cluster bootstrap."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_family(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result.loc[result["family"].str.startswith("single_task:"), "family"] = "single_task_mlp"
    return result


def paired_bootstrap(
    predictions: pd.DataFrame,
    candidate: str,
    reference: str,
    replicates: int,
    seed: int,
) -> dict[str, float]:
    candidate_rows = predictions[predictions["family"] == candidate]
    reference_rows = predictions[predictions["family"] == reference]
    keys = ["seed", "task", "molecule_id", "component_id"]
    paired = candidate_rows.merge(
        reference_rows,
        on=keys,
        suffixes=("_candidate", "_reference"),
        validate="one_to_one",
    )
    paired = paired[np.isfinite(paired["y_true_candidate"])].copy()
    if not np.array_equal(paired["y_true_candidate"], paired["y_true_reference"]):
        raise RuntimeError("candidate/reference labels do not match")
    seeds = np.sort(paired["seed"].unique())
    tasks = np.sort(paired["task"].unique())
    blocks = {}
    for model_seed in seeds:
        for task in tasks:
            subset = paired[(paired["seed"] == model_seed) & (paired["task"] == task)].reset_index(
                drop=True
            )
            component_rows = [
                np.asarray(indices, dtype=int)
                for indices in subset.groupby("component_id", sort=False).indices.values()
            ]
            blocks[(model_seed, task)] = (
                subset["y_true_candidate"].to_numpy(dtype=int),
                subset["y_score_candidate"].to_numpy(),
                subset["y_score_reference"].to_numpy(),
                component_rows,
            )
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(replicates):
        seed_draw = rng.choice(seeds, size=len(seeds), replace=True)
        seed_differences = []
        for model_seed in seed_draw:
            task_differences = []
            for task in tasks:
                truth_all, candidate_all, reference_all, component_rows = blocks[(model_seed, task)]
                sampled_components = rng.integers(0, len(component_rows), size=len(component_rows))
                sampled_rows = np.concatenate(
                    [component_rows[index] for index in sampled_components]
                )
                truth = truth_all[sampled_rows]
                if len(np.unique(truth)) < 2:
                    continue
                candidate_score = average_precision_score(truth, candidate_all[sampled_rows])
                reference_score = average_precision_score(truth, reference_all[sampled_rows])
                task_differences.append(candidate_score - reference_score)
            if task_differences:
                seed_differences.append(float(np.mean(task_differences)))
        if seed_differences:
            values.append(float(np.mean(seed_differences)))
    if not values:
        raise RuntimeError("bootstrap produced no valid paired replicates")

    observed = []
    for (model_seed, task), subset in paired.groupby(["seed", "task"]):
        del model_seed, task
        truth = subset["y_true_candidate"].to_numpy(dtype=int)
        observed.append(
            average_precision_score(truth, subset["y_score_candidate"])
            - average_precision_score(truth, subset["y_score_reference"])
        )
    return {
        "observed_macro_delta": float(np.mean(observed)),
        "bootstrap_mean": float(np.mean(values)),
        "ci_low": float(np.percentile(values, 2.5)),
        "ci_high": float(np.percentile(values, 97.5)),
        "replicates": len(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--candidate", default="shared_primary")
    parser.add_argument("--reference", default="single_task_mlp")
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20261020)
    args = parser.parse_args()
    metrics_paths = [path / "metrics.csv" for path in args.runs]
    prediction_paths = [path / "predictions.parquet" for path in args.runs]
    metrics = normalize_family(pd.concat([pd.read_csv(path) for path in metrics_paths]))
    predictions = normalize_family(
        pd.concat([pd.read_parquet(path) for path in prediction_paths], ignore_index=True)
    )
    run_manifests = [json.loads((path / "manifest.json").read_text()) for path in args.runs]
    confirmatory = all(manifest.get("confirmatory_eligible", False) for manifest in run_manifests)
    metric_columns = [
        column
        for column in (
            "pr_auc",
            "bedroc20",
            "ef1",
            "ef5",
            "precision_at_1",
            "recall_at_1",
            "roc_auc",
            "brier",
            "ece10",
        )
        if column in metrics
    ]
    summary = metrics.groupby(["family", "task"])[metric_columns].agg(["mean", "std"]).reset_index()
    macro = (
        metrics.groupby(["family", "seed"])["pr_auc"]
        .mean()
        .groupby("family")
        .agg(["mean", "std"])
        .sort_values("mean", ascending=False)
    )
    comparison = paired_bootstrap(
        predictions,
        args.candidate,
        args.reference,
        args.bootstrap,
        args.seed,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.out.with_suffix(".csv"), index=False)

    lines = [
        "# ChEMBL 37 activity-only baseline results"
        if confirmatory
        else "# Exploratory baseline results",
        "",
        (
            "> **Confirmatory activity branch only.** These results use the frozen ChEMBL 37 "
            "cohort, but contain no authorized VietHerb bags and do not test the central MIL claim."
            if confirmatory
            else "> **Not confirmatory.** These results use a live ChEMBL REST snapshot and "
            "contain no authorized VietHerb bags."
        ),
        "",
        f"Generated at {datetime.now(UTC).isoformat()} from five fixed seeds.",
        "",
        "## Macro PR-AUC",
        "",
        "| Model | Mean | SD |",
        "|---|---:|---:|",
    ]
    for family, row in macro.iterrows():
        lines.append(f"| {family} | {row['mean']:.4f} | {row['std']:.4f} |")
    lines.extend(
        [
            "",
            "## Per-target PR-AUC",
            "",
            "| Model | Target | Mean | SD |",
            "|---|---|---:|---:|",
        ]
    )
    for _, row in summary.iterrows():
        lines.append(
            f"| {row[('family', '')]} | {row[('task', '')]} | "
            f"{row[('pr_auc', 'mean')]:.4f} | {row[('pr_auc', 'std')]:.4f} |"
        )
    lines.extend(
        [
            "",
            f"## Paired {args.candidate} minus {args.reference}",
            "",
            f"Observed macro PR-AUC difference: **{comparison['observed_macro_delta']:+.4f}**. "
            f"Hierarchical seed + chemical-component bootstrap 95% CI: "
            f"**[{comparison['ci_low']:+.4f}, {comparison['ci_high']:+.4f}]** "
            f"({comparison['replicates']} replicates).",
            "",
            "The comparison evaluates the activity-only branch. "
            "It does not test the paper's ethnopharmacology/MIL hypothesis.",
            "",
            "## Input hashes",
            "",
        ]
    )
    for path in [*metrics_paths, *prediction_paths]:
        lines.append(f"- `{path}`: `{sha256(path)}`")
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    args.out.with_suffix(".json").write_text(
        json.dumps(comparison, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(comparison, indent=2))


if __name__ == "__main__":
    main()

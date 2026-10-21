#!/usr/bin/env python3
"""Run the official Chemprop D-MPNN on a frozen custom split and fixed seeds."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

from vietherb_mtl import (
    bedroc_score,
    ef1_score,
    ef5_score,
    expected_calibration_error,
    pr_auc_score,
    precision_recall_at_fraction,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_metric(name: str, labels: np.ndarray, scores: np.ndarray) -> float:
    finite = np.isfinite(labels) & np.isfinite(scores)
    labels, scores = labels[finite].astype(int), scores[finite]
    if not len(labels) or len(np.unique(labels)) < 2:
        return math.nan
    if name == "pr_auc":
        return pr_auc_score(labels, scores)
    if name == "bedroc20":
        return bedroc_score(labels, scores, alpha=20.0)
    if name == "ef1":
        return ef1_score(labels, scores)
    if name == "ef5":
        return ef5_score(labels, scores)
    if name == "precision_at_1":
        return precision_recall_at_fraction(labels, scores, fraction=0.01)[0]
    if name == "recall_at_1":
        return precision_recall_at_fraction(labels, scores, fraction=0.01)[1]
    if name == "roc_auc":
        return float(roc_auc_score(labels, scores))
    if name == "brier":
        return float(brier_score_loss(labels, scores))
    if name == "ece10":
        return expected_calibration_error(labels, scores, n_bins=10)
    raise ValueError(f"unknown metric: {name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--chemprop", type=Path, default=Path(".venv/Scripts/chemprop.exe"))
    parser.add_argument("--seeds", type=int, nargs="+", default=[13, 37, 71, 101, 137])
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--patience", type=int, default=12)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()) and not args.overwrite:
        raise FileExistsError(f"{args.out} is not empty; pass --overwrite explicitly")
    args.out.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_parquet(args.dataset_dir / "model_table.parquet")
    exported = pd.read_csv(args.input)
    tasks = [column for column in exported if column.startswith("activity_")]
    test = dataset[dataset["split"] == "test"].reset_index(drop=True)
    metrics = (
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
    metric_rows, prediction_rows = [], []
    for seed in args.seeds:
        seed_dir = args.out / f"seed_{seed}"
        command = [
            str(args.chemprop),
            "train",
            "--data-path",
            str(args.input),
            "--output-dir",
            str(seed_dir),
            "--smiles-columns",
            "canonical_smiles",
            "--target-columns",
            *tasks,
            "--ignore-columns",
            "molecule_id",
            "component_id",
            "--splits-column",
            "split",
            "--task-type",
            "classification",
            "--loss-function",
            "bce",
            "--metrics",
            "accuracy",
            "--tracking-metric",
            "val_loss",
            "--message-hidden-dim",
            "300",
            "--depth",
            "3",
            "--dropout",
            "0.1",
            "--ffn-hidden-dim",
            "300",
            "--ffn-num-layers",
            "2",
            "--batch-size",
            "256",
            "--epochs",
            str(args.epochs),
            "--warmup-epochs",
            "2",
            "--patience",
            str(args.patience),
            "--num-workers",
            "0",
            "--accelerator",
            "gpu",
            "--devices",
            "1",
            "--pytorch-seed",
            str(seed),
            "--data-seed",
            str(seed),
            "--remove-checkpoints",
        ]
        print(f"Chemprop D-MPNN seed={seed}", flush=True)
        log_path = args.out / f"seed_{seed}.log"
        with log_path.open("w", encoding="utf-8") as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        prediction_path = seed_dir / "model_0" / "test_predictions.csv"
        scores = pd.read_csv(prediction_path)
        if len(scores) != len(test):
            raise RuntimeError(f"Chemprop test row count mismatch for seed {seed}")
        if not np.array_equal(scores["canonical_smiles"], test["canonical_smiles"]):
            raise RuntimeError(f"Chemprop test row order mismatch for seed {seed}")
        for task in tasks:
            truth = test[task].to_numpy(dtype=float)
            task_scores = scores[task].to_numpy(dtype=float)
            row = {
                "task": task,
                "n": int(np.isfinite(truth).sum()),
                "family": "chemprop_dmpnn",
                "seed": seed,
                "aux_weight": 0.0,
                "importance_weighting": False,
                "evaluation_split": "test",
            }
            row.update({name: safe_metric(name, truth, task_scores) for name in metrics})
            metric_rows.append(row)
            for index in np.flatnonzero(np.isfinite(truth)):
                prediction_rows.append(
                    {
                        "molecule_id": test.loc[index, "molecule_id"],
                        "task": task,
                        "y_true": int(truth[index]),
                        "y_score": float(task_scores[index]),
                        "is_natural_product": bool(test.loc[index, "is_natural_product"]),
                        "component_id": test.loc[index, "component_id"],
                        "murcko_scaffold": test.loc[index, "murcko_scaffold"],
                        "family": "chemprop_dmpnn",
                        "seed": seed,
                        "aux_weight": 0.0,
                        "importance_weighting": False,
                        "evaluation_split": "test",
                    }
                )
        pd.DataFrame(metric_rows).to_csv(args.out / "metrics.csv", index=False)
        pd.DataFrame(prediction_rows).to_parquet(args.out / "predictions.parquet", index=False)
    dataset_manifest = json.loads(
        (args.dataset_dir / "manifest.json").read_text(encoding="utf-8")
    )
    manifest = {
        "experiment": "chembl37_chemprop_dmpnn_v1",
        "finished_at": datetime.now(UTC).isoformat(),
        "chemprop": importlib.metadata.version("chemprop"),
        "python": platform.python_version(),
        "seeds": args.seeds,
        "epochs": args.epochs,
        "patience": args.patience,
        "early_stopping_metric": "validation_loss",
        "test_evaluated_after_best_validation_checkpoint": True,
        "rows": len(dataset),
        "synthetic": False,
        "confirmatory_eligible": bool(dataset_manifest.get("confirmatory_eligible", False)),
        "scientific_results": True,
        "input_sha256": sha256(args.input),
        "dataset_manifest_sha256": sha256(args.dataset_dir / "manifest.json"),
        "metrics_sha256": sha256(args.out / "metrics.csv"),
        "predictions_sha256": sha256(args.out / "predictions.parquet"),
    }
    (args.out / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

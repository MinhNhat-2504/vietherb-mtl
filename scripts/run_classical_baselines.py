#!/usr/bin/env python3
"""Run strong fixed-hyperparameter fingerprint baselines."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score

from vietherb_mtl import (
    FingerprintConfig,
    FingerprintEncoder,
    bedroc_score,
    ef1_score,
    ef5_score,
    expected_calibration_error,
    pr_auc_score,
    precision_recall_at_fraction,
)


def safe_metric(name: str, labels: np.ndarray, scores: np.ndarray) -> float:
    if len(np.unique(labels)) < 2:
        return math.nan
    if name == "pr_auc":
        return pr_auc_score(labels.tolist(), scores.tolist())
    if name == "bedroc20":
        return bedroc_score(labels.tolist(), scores.tolist(), alpha=20.0)
    if name == "ef1":
        return ef1_score(labels.tolist(), scores.tolist())
    if name == "ef5":
        return ef5_score(labels.tolist(), scores.tolist())
    if name == "precision_at_1":
        return precision_recall_at_fraction(labels.tolist(), scores.tolist(), fraction=0.01)[0]
    if name == "recall_at_1":
        return precision_recall_at_fraction(labels.tolist(), scores.tolist(), fraction=0.01)[1]
    if name == "roc_auc":
        return float(roc_auc_score(labels, scores))
    if name == "brier":
        return float(brier_score_loss(labels, scores))
    if name == "ece10":
        return expected_calibration_error(labels.tolist(), scores.tolist(), n_bins=10)
    raise ValueError(f"unknown metric: {name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()) and not args.overwrite:
        raise FileExistsError(f"{args.out} is not empty; pass --overwrite explicitly")
    args.out.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    dataset_dir = Path(config["dataset_dir"])
    frame = pd.read_parquet(dataset_dir / "model_table.parquet")
    tasks = list(config["tasks"]["primary"])
    metrics = list(config["evaluation"]["metrics"])
    encoder = FingerprintEncoder(
        FingerprintConfig(n_bits=int(config["model"]["input_dim"]), backend="auto")
    )
    features = np.asarray(encoder.transform(frame["canonical_smiles"].tolist()), dtype=np.uint8)
    split = frame["split"].to_numpy()
    results, predictions = [], []
    for seed in config["seeds"]:
        estimators = {
            "logistic_regression": LogisticRegression(
                C=1.0,
                class_weight="balanced",
                max_iter=1000,
                solver="liblinear",
                random_state=int(seed),
            ),
            "extra_trees": ExtraTreesClassifier(
                n_estimators=300,
                max_features="sqrt",
                min_samples_leaf=2,
                class_weight="balanced",
                n_jobs=1,
                random_state=int(seed),
            ),
        }
        for task in tasks:
            labels = frame[task].to_numpy(dtype=np.float32)
            train = np.flatnonzero((split == "train") & np.isfinite(labels))
            test = np.flatnonzero((split == "test") & np.isfinite(labels))
            for family, prototype in estimators.items():
                estimator = prototype.__class__(**prototype.get_params())
                print(f"fit family={family} task={task} seed={seed}", flush=True)
                estimator.fit(features[train], labels[train].astype(int))
                scores = estimator.predict_proba(features[test])[:, 1]
                row = {
                    "task": task,
                    "n": len(test),
                    "family": family,
                    "seed": int(seed),
                    "aux_weight": 0.0,
                    "importance_weighting": False,
                }
                for metric in metrics:
                    row[metric] = safe_metric(metric, labels[test].astype(int), scores)
                results.append(row)
                subset = frame.iloc[test]
                for molecule_id, truth, score, is_np, component_id, scaffold in zip(
                    subset["molecule_id"],
                    labels[test],
                    scores,
                    subset["is_natural_product"],
                    subset["component_id"],
                    subset["murcko_scaffold"],
                    strict=True,
                ):
                    predictions.append(
                        {
                            "molecule_id": molecule_id,
                            "task": task,
                            "y_true": int(truth),
                            "y_score": float(score),
                            "is_natural_product": bool(is_np),
                            "component_id": component_id,
                            "murcko_scaffold": scaffold,
                            "family": family,
                            "seed": int(seed),
                            "aux_weight": 0.0,
                            "importance_weighting": False,
                        }
                    )
    pd.DataFrame(results).to_csv(args.out / "metrics.csv", index=False)
    pd.DataFrame(predictions).to_parquet(args.out / "predictions.parquet", index=False)
    dataset_manifest = json.loads((dataset_dir / "manifest.json").read_text())
    manifest = {
        "experiment": config["experiment_name"] + "_classical",
        "finished_at": datetime.now(UTC).isoformat(),
        "config_sha256": hashlib.sha256(args.config.read_bytes()).hexdigest(),
        "python": platform.python_version(),
        "sklearn": __import__("sklearn").__version__,
        "fingerprint_backend": encoder.backend,
        "rows": len(frame),
        "synthetic": bool(dataset_manifest.get("synthetic", False)),
        "confirmatory_eligible": bool(dataset_manifest.get("confirmatory_eligible", False)),
        "scientific_results": not bool(dataset_manifest.get("synthetic", False)),
        "dataset_manifest_sha256": hashlib.sha256(
            (dataset_dir / "manifest.json").read_bytes()
        ).hexdigest(),
        "metrics_sha256": hashlib.sha256((args.out / "metrics.csv").read_bytes()).hexdigest(),
        "predictions_sha256": hashlib.sha256(
            (args.out / "predictions.parquet").read_bytes()
        ).hexdigest(),
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

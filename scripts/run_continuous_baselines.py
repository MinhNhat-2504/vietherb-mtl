#!/usr/bin/env python3
"""Run five-seed continuous-pChEMBL single-task and shared MLP sensitivity."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import platform
import random
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
import torch
import yaml
from torch.utils.data import DataLoader, TensorDataset

from vietherb_mtl import (
    FingerprintConfig,
    FingerprintEncoder,
    ModelConfig,
    MultiTaskMLP,
    mean_absolute_error,
    root_mean_squared_error,
    spearman_correlation,
)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def evaluate(
    model: MultiTaskMLP,
    features: torch.Tensor,
    labels: dict[str, np.ndarray],
    indices: np.ndarray,
    tasks: list[str],
    normalizers: dict[str, tuple[float, float]],
    device: torch.device,
) -> tuple[list[dict], dict[str, np.ndarray]]:
    model.eval()
    with torch.no_grad():
        outputs = model(features[indices].to(device))
    rows: list[dict] = []
    predictions: dict[str, np.ndarray] = {}
    for task in tasks:
        mean, scale = normalizers[task]
        scores = outputs[task].cpu().numpy() * scale + mean
        truth = labels[task][indices]
        finite = np.isfinite(truth) & np.isfinite(scores)
        truth_finite, score_finite = truth[finite], scores[finite]
        row = {"task": task, "n": int(finite.sum())}
        if finite.sum() >= 2:
            row.update(
                {
                    "mae": mean_absolute_error(truth_finite, score_finite),
                    "rmse": root_mean_squared_error(truth_finite, score_finite),
                    "spearman": spearman_correlation(truth_finite, score_finite),
                }
            )
        else:
            row.update({"mae": math.nan, "rmse": math.nan, "spearman": math.nan})
        rows.append(row)
        predictions[task] = scores
    return rows, predictions


def train_one(
    features_np: np.ndarray,
    labels_np: dict[str, np.ndarray],
    frame: pd.DataFrame,
    tasks: list[str],
    family: str,
    seed: int,
    config: dict,
    device: torch.device,
) -> tuple[list[dict], pd.DataFrame]:
    set_seed(seed)
    active_tasks = [family.split(":", 1)[1]] if family.startswith("single_task:") else tasks
    split = frame["split"].to_numpy()
    train_indices = np.flatnonzero(split == "train")
    validation_indices = np.flatnonzero(split == "validation")
    test_indices = np.flatnonzero(split == "test")
    normalizers = {}
    normalized_labels = {}
    for task in active_tasks:
        train_values = labels_np[task][train_indices]
        train_values = train_values[np.isfinite(train_values)]
        mean = float(train_values.mean())
        scale = max(float(train_values.std()), 1e-6)
        normalizers[task] = (mean, scale)
        normalized_labels[task] = (labels_np[task] - mean) / scale

    model = MultiTaskMLP(
        ModelConfig(
            input_dim=features_np.shape[1],
            hidden_dims=tuple(config["model"]["hidden_dims"]),
            primary_tasks=tuple(active_tasks),
            auxiliary_tasks=(),
            dropout=float(config["model"]["dropout"]),
            auxiliary_weight=0.0,
        )
    ).to(device)
    training = config["training"]
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(training["learning_rate"]),
        weight_decay=float(training["weight_decay"]),
    )
    features = torch.as_tensor(features_np, dtype=torch.float32)
    label_tensors = {
        task: torch.as_tensor(values, dtype=torch.float32)
        for task, values in normalized_labels.items()
    }
    loader = DataLoader(
        TensorDataset(torch.as_tensor(train_indices, dtype=torch.long)),
        batch_size=int(training["batch_size"]),
        shuffle=True,
        generator=torch.Generator().manual_seed(seed),
    )
    best_score, best_epoch, stale, best_state = math.inf, 0, 0, None
    for epoch in range(1, int(training["epochs"]) + 1):
        model.train()
        for (batch_cpu,) in loader:
            batch = batch_cpu.numpy()
            outputs = model(features[batch].to(device))
            losses = []
            for task in active_tasks:
                targets = label_tensors[task][batch].to(device)
                valid = torch.isfinite(targets)
                if bool(valid.any()):
                    losses.append(torch.square(outputs[task][valid] - targets[valid]).mean())
            if not losses:
                continue
            loss = torch.stack(losses).mean()
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
        validation_rows, _ = evaluate(
            model,
            features,
            labels_np,
            validation_indices,
            active_tasks,
            normalizers,
            device,
        )
        values = [row["mae"] for row in validation_rows if math.isfinite(row["mae"])]
        score = float(np.mean(values)) if values else math.inf
        if score < best_score - 1e-6:
            best_score, best_epoch, stale = score, epoch, 0
            best_state = copy.deepcopy(
                {key: value.detach().cpu() for key, value in model.state_dict().items()}
            )
        else:
            stale += 1
            if stale >= int(training["early_stopping_patience"]):
                break
    if best_state is None:
        raise RuntimeError("no finite validation MAE")
    model.load_state_dict(best_state)
    rows, predictions = evaluate(
        model, features, labels_np, test_indices, active_tasks, normalizers, device
    )
    for row in rows:
        row.update(
            {
                "family": family,
                "seed": seed,
                "best_epoch": best_epoch,
                "validation_macro_mae": best_score,
            }
        )
    prediction_rows = []
    subset = frame.iloc[test_indices]
    for task, scores in predictions.items():
        for molecule_id, truth, score, component_id, scaffold in zip(
            subset["molecule_id"],
            labels_np[task][test_indices],
            scores,
            subset["component_id"],
            subset["murcko_scaffold"],
            strict=True,
        ):
            if np.isfinite(truth):
                prediction_rows.append(
                    {
                        "molecule_id": molecule_id,
                        "task": task,
                        "y_true": float(truth),
                        "y_score": float(score),
                        "component_id": component_id,
                        "murcko_scaffold": scaffold,
                        "family": family,
                        "seed": seed,
                    }
                )
    return rows, pd.DataFrame(prediction_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    output_dir = Path(config["output_dir"])
    if output_dir.exists() and any(output_dir.iterdir()) and not args.overwrite:
        raise FileExistsError(f"{output_dir} is not empty; pass --overwrite explicitly")
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_dir = Path(config["dataset_dir"])
    frame = pd.read_parquet(dataset_dir / "model_table.parquet")
    tasks = list(config["tasks"]["primary"])
    encoder = FingerprintEncoder(
        FingerprintConfig(n_bits=int(config["model"]["input_dim"]), backend="auto")
    )
    features = np.asarray(encoder.transform(frame["canonical_smiles"].tolist()), dtype=np.float32)
    labels = {task: frame[task].to_numpy(dtype=np.float32) for task in tasks}
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    all_rows, all_predictions = [], []
    families = [*(f"single_task:{task}" for task in tasks), "shared_continuous"]
    for seed in config["seeds"]:
        for family in families:
            print(f"run family={family} seed={seed}", flush=True)
            rows, predictions = train_one(
                features, labels, frame, tasks, family, int(seed), config, device
            )
            all_rows.extend(rows)
            all_predictions.append(predictions)
            pd.DataFrame(all_rows).to_csv(output_dir / "metrics.csv", index=False)
            pd.concat(all_predictions, ignore_index=True).to_parquet(
                output_dir / "predictions.parquet", index=False
            )
    dataset_manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest = {
        "experiment": config["experiment_name"],
        "finished_at": datetime.now(UTC).isoformat(),
        "config_sha256": hashlib.sha256(args.config.read_bytes()).hexdigest(),
        "dataset_manifest_sha256": hashlib.sha256(
            (dataset_dir / "manifest.json").read_bytes()
        ).hexdigest(),
        "metrics_sha256": hashlib.sha256((output_dir / "metrics.csv").read_bytes()).hexdigest(),
        "predictions_sha256": hashlib.sha256(
            (output_dir / "predictions.parquet").read_bytes()
        ).hexdigest(),
        "device": str(device),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "fingerprint_backend": encoder.backend,
        "rows": len(frame),
        "synthetic": False,
        "confirmatory_eligible": bool(dataset_manifest.get("confirmatory_eligible", False)),
        "scientific_results": True,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

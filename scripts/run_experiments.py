#!/usr/bin/env python3
"""Run the preregistered MLP baseline/ablation matrix."""

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
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from torch.nn import functional as F
from torch.utils.data import DataLoader, TensorDataset

from vietherb_mtl import (
    AttentionMILAggregator,
    FingerprintConfig,
    FingerprintEncoder,
    ModelConfig,
    MultiTaskMLP,
    bag_nnpu_loss,
    bedroc_score,
    ef1_score,
    nnpu_loss,
    pr_auc_score,
)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def config_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_metric(name: str, labels: np.ndarray, scores: np.ndarray) -> float:
    finite = np.isfinite(labels) & np.isfinite(scores)
    labels, scores = labels[finite].astype(int), scores[finite]
    if len(labels) == 0 or len(np.unique(labels)) < 2:
        return math.nan
    if name == "pr_auc":
        return pr_auc_score(labels.tolist(), scores.tolist())
    if name == "bedroc20":
        return bedroc_score(labels.tolist(), scores.tolist(), alpha=20.0)
    if name == "ef1":
        return ef1_score(labels.tolist(), scores.tolist())
    if name == "roc_auc":
        return float(roc_auc_score(labels, scores))
    if name == "brier":
        return float(brier_score_loss(labels, scores))
    raise ValueError(f"unknown metric: {name}")


def estimate_domain_weights(
    features: np.ndarray, is_natural: np.ndarray, train_indices: np.ndarray
) -> np.ndarray:
    weights = np.ones(len(features), dtype=np.float32)
    train_domain = is_natural[train_indices].astype(int)
    if len(np.unique(train_domain)) < 2:
        return weights
    classifier = LogisticRegression(
        penalty="l2", C=1.0, max_iter=500, solver="liblinear", random_state=0
    )
    classifier.fit(features[train_indices], train_domain)
    probability = np.clip(classifier.predict_proba(features)[:, 1], 1e-3, 1 - 1e-3)
    prior_odds = (train_domain == 0).sum() / max((train_domain == 1).sum(), 1)
    weights = np.clip(probability / (1 - probability) * prior_odds, 0.2, 5.0)
    return weights.astype(np.float32)


def masked_weighted_bce(
    logits: torch.Tensor,
    targets: torch.Tensor,
    sample_weights: torch.Tensor,
    pos_weight: torch.Tensor,
) -> torch.Tensor:
    valid = torch.isfinite(targets)
    clean = torch.where(valid, targets, torch.zeros_like(targets))
    losses = F.binary_cross_entropy_with_logits(
        logits, clean, pos_weight=pos_weight, reduction="none"
    )
    weighted = losses * sample_weights * valid
    return weighted.sum() / (sample_weights * valid).sum().clamp_min(1.0)


def pack_bags(
    selected_bags: np.ndarray,
    membership_lookup: dict[str, np.ndarray],
    molecule_lookup: dict[str, int],
) -> tuple[np.ndarray, np.ndarray]:
    instance_indices: list[int] = []
    bag_indices: list[int] = []
    for packed_id, bag_id in enumerate(selected_bags):
        molecule_ids = membership_lookup[str(bag_id)]
        for molecule_id in molecule_ids:
            instance_indices.append(molecule_lookup[str(molecule_id)])
            bag_indices.append(packed_id)
    if not instance_indices:
        raise ValueError("selected MIL bags contain no molecule instances")
    return np.asarray(instance_indices), np.asarray(bag_indices)


def evaluate(
    model: MultiTaskMLP,
    features: torch.Tensor,
    labels: dict[str, np.ndarray],
    indices: np.ndarray,
    primary_tasks: list[str],
    metrics: list[str],
    device: torch.device,
) -> tuple[list[dict], dict[str, np.ndarray]]:
    model.eval()
    with torch.no_grad():
        logits = model(features[indices].to(device))
    rows, predictions = [], {}
    for task in primary_tasks:
        scores = torch.sigmoid(logits[task]).cpu().numpy()
        truth = labels[task][indices]
        predictions[task] = scores
        row = {"task": task, "n": int(np.isfinite(truth).sum())}
        for metric in metrics:
            row[metric] = safe_metric(metric, truth, scores)
        rows.append(row)
    return rows, predictions


def train_one(
    *,
    features_np: np.ndarray,
    labels_np: dict[str, np.ndarray],
    frame: pd.DataFrame,
    primary_tasks: list[str],
    auxiliary_tasks: list[str],
    pu_priors: dict[str, float],
    bags: pd.DataFrame | None,
    bag_membership: pd.DataFrame | None,
    family: str,
    aux_weight: float,
    use_importance: bool,
    seed: int,
    config: dict,
    device: torch.device,
) -> tuple[list[dict], pd.DataFrame, int]:
    set_seed(seed)
    active_primary = primary_tasks
    if family.startswith("single_task:"):
        active_primary = [family.split(":", 1)[1]]
    use_naive_auxiliary = family == "naive_broadcast" and aux_weight > 0
    use_mil = family in {"mil_aux", "permuted_mil"} and aux_weight > 0
    model = MultiTaskMLP(
        ModelConfig(
            input_dim=features_np.shape[1],
            hidden_dims=tuple(config["model"]["hidden_dims"]),
            primary_tasks=tuple(active_primary),
            auxiliary_tasks=tuple(auxiliary_tasks),
            dropout=float(config["model"]["dropout"]),
            auxiliary_weight=aux_weight,
        )
    ).to(device)
    training = config["training"]
    mil = None
    parameters = list(model.parameters())
    if use_mil:
        if bags is None or bag_membership is None:
            raise ValueError(f"{family} requires bags.parquet and bag_membership.parquet")
        mil = AttentionMILAggregator(
            embedding_dim=int(config["model"]["hidden_dims"][-1]),
            output_dim=len(auxiliary_tasks),
            attention_dim=int(config["model"].get("attention_dim", 128)),
        ).to(device)
        parameters.extend(mil.parameters())
    optimizer = torch.optim.AdamW(
        parameters,
        lr=float(training["learning_rate"]),
        weight_decay=float(training["weight_decay"]),
    )
    split = frame["split"].to_numpy()
    train_indices = np.flatnonzero(split == "train")
    validation_indices = np.flatnonzero(split == "validation")
    test_indices = np.flatnonzero(split == "test")
    features = torch.as_tensor(features_np, dtype=torch.float32)
    importance = (
        estimate_domain_weights(features_np, frame["is_natural_product"].to_numpy(), train_indices)
        if use_importance
        else np.ones(len(frame), dtype=np.float32)
    )
    label_tensors = {
        task: torch.as_tensor(values, dtype=torch.float32) for task, values in labels_np.items()
    }
    positive_weights = {}
    for task in active_primary:
        values = labels_np[task][train_indices]
        finite = values[np.isfinite(values)]
        positives = max(float((finite == 1).sum()), 1.0)
        negatives = max(float((finite == 0).sum()), 1.0)
        positive_weights[task] = torch.tensor(negatives / positives, device=device)

    molecule_aux = {task: values.copy() for task, values in labels_np.items()}
    bag_labels = None
    membership_lookup = None
    molecule_lookup = None
    train_bag_ids = None
    if use_mil:
        assert bags is not None and bag_membership is not None
        bag_labels = bags.set_index("bag_id")[auxiliary_tasks].copy()
        bag_labels.index = bag_labels.index.astype(str)
        train_bag_ids = bags.loc[bags["split"] == "train", "bag_id"].astype(str).to_numpy()
        if family == "permuted_mil":
            rng_bags = np.random.default_rng(seed)
            for task in auxiliary_tasks:
                bag_labels.loc[train_bag_ids, task] = rng_bags.permutation(
                    bag_labels.loc[train_bag_ids, task].to_numpy()
                )
        membership_lookup = {
            str(bag_id): group["molecule_id"].astype(str).to_numpy()
            for bag_id, group in bag_membership.groupby("bag_id")
        }
        molecule_lookup = {
            str(molecule_id): index for index, molecule_id in enumerate(frame["molecule_id"])
        }

    dataset = TensorDataset(torch.as_tensor(train_indices, dtype=torch.long))
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(
        dataset,
        batch_size=int(training["batch_size"]),
        shuffle=True,
        generator=generator,
    )
    rng = np.random.default_rng(seed)
    best_score, best_epoch, stale, best_state = -math.inf, 0, 0, None
    for epoch in range(1, int(training["epochs"]) + 1):
        model.train()
        if mil is not None:
            mil.train()
        for (batch_indices_cpu,) in loader:
            batch_indices = batch_indices_cpu.numpy()
            outputs = model(features[batch_indices].to(device))
            sample_weights = torch.as_tensor(importance[batch_indices], device=device)
            primary_losses = []
            for task in active_primary:
                primary_losses.append(
                    masked_weighted_bce(
                        outputs[task],
                        label_tensors[task][batch_indices].to(device),
                        sample_weights,
                        positive_weights[task],
                    )
                )
            loss = torch.stack(primary_losses).mean()
            if use_naive_auxiliary:
                pu_losses = []
                pu_size = int(training.get("pu_batch_size", training["batch_size"]))
                for task in auxiliary_tasks:
                    values = molecule_aux[task]
                    positives = train_indices[values[train_indices] == 1]
                    unlabeled = train_indices[values[train_indices] == 0]
                    if len(positives) == 0 or len(unlabeled) == 0:
                        continue
                    pos_pick = rng.choice(positives, size=max(1, pu_size // 2), replace=True)
                    unl_pick = rng.choice(unlabeled, size=max(1, pu_size // 2), replace=True)
                    pu_indices = np.concatenate([pos_pick, unl_pick])
                    pu_logits = model(features[pu_indices].to(device))[task]
                    pu_targets = torch.as_tensor(
                        values[pu_indices], dtype=torch.float32, device=device
                    )
                    pu_losses.append(nnpu_loss(pu_logits, pu_targets, prior=pu_priors[task]))
                if pu_losses:
                    loss = loss + aux_weight * torch.stack(pu_losses).mean()
            if use_mil:
                assert mil is not None
                assert bag_labels is not None
                assert train_bag_ids is not None
                assert membership_lookup is not None
                assert molecule_lookup is not None
                bag_losses = []
                pu_size = int(training.get("pu_batch_size", training["batch_size"]))
                half_size = max(1, pu_size // 2)
                for task_index, task in enumerate(auxiliary_tasks):
                    values = bag_labels.loc[train_bag_ids, task].to_numpy(dtype=np.float32)
                    positives = train_bag_ids[values == 1]
                    unlabeled = train_bag_ids[values == 0]
                    if len(positives) == 0 or len(unlabeled) == 0:
                        continue
                    selected = np.concatenate(
                        [
                            rng.choice(positives, size=half_size, replace=True),
                            rng.choice(unlabeled, size=half_size, replace=True),
                        ]
                    )
                    instance_indices, bag_index = pack_bags(
                        selected, membership_lookup, molecule_lookup
                    )
                    embeddings = model.encode(features[instance_indices].to(device))
                    bag_logits, _ = mil(
                        embeddings,
                        torch.as_tensor(bag_index, dtype=torch.long, device=device),
                    )
                    bag_targets = torch.cat(
                        [
                            torch.ones(half_size, device=device),
                            torch.zeros(half_size, device=device),
                        ]
                    )
                    bag_losses.append(
                        bag_nnpu_loss(bag_logits[:, task_index], bag_targets, prior=pu_priors[task])
                    )
                if bag_losses:
                    loss = loss + aux_weight * torch.stack(bag_losses).mean()
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()

        validation_rows, _ = evaluate(
            model,
            features,
            labels_np,
            validation_indices,
            active_primary,
            ["pr_auc"],
            device,
        )
        score_values = [row["pr_auc"] for row in validation_rows if math.isfinite(row["pr_auc"])]
        score = float(np.mean(score_values)) if score_values else -math.inf
        if score > best_score + 1e-6:
            best_score, best_epoch, stale = score, epoch, 0
            best_state = {
                "model": copy.deepcopy(
                    {key: value.detach().cpu() for key, value in model.state_dict().items()}
                ),
                "mil": None
                if mil is None
                else copy.deepcopy(
                    {key: value.detach().cpu() for key, value in mil.state_dict().items()}
                ),
            }
        else:
            stale += 1
            if stale >= int(training["early_stopping_patience"]):
                break
    if best_state is None:
        raise RuntimeError("no valid validation metric; inspect split class counts")
    model.load_state_dict(best_state["model"])
    if mil is not None and best_state["mil"] is not None:
        mil.load_state_dict(best_state["mil"])
    metric_names = list(config["evaluation"]["metrics"])
    test_rows, predictions = evaluate(
        model, features, labels_np, test_indices, active_primary, metric_names, device
    )
    for row in test_rows:
        row.update(
            {
                "family": family,
                "seed": seed,
                "aux_weight": aux_weight,
                "importance_weighting": use_importance,
                "best_epoch": best_epoch,
                "validation_macro_pr_auc": best_score,
            }
        )
    prediction_rows = []
    for task, scores in predictions.items():
        subset = frame.iloc[test_indices]
        for molecule_id, truth, score, is_np, component_id, scaffold in zip(
            subset["molecule_id"],
            labels_np[task][test_indices],
            scores,
            subset["is_natural_product"],
            subset["component_id"],
            subset["murcko_scaffold"],
            strict=True,
        ):
            prediction_rows.append(
                {
                    "molecule_id": molecule_id,
                    "task": task,
                    "y_true": truth,
                    "y_score": float(score),
                    "is_natural_product": bool(is_np),
                    "component_id": component_id,
                    "murcko_scaffold": scaffold,
                    "family": family,
                    "seed": seed,
                    "aux_weight": aux_weight,
                    "importance_weighting": use_importance,
                }
            )
    return test_rows, pd.DataFrame(prediction_rows), best_epoch


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
    bags_path = dataset_dir / "bags.parquet"
    membership_path = dataset_dir / "bag_membership.parquet"
    bags = pd.read_parquet(bags_path) if bags_path.exists() else None
    bag_membership = pd.read_parquet(membership_path) if membership_path.exists() else None
    primary_tasks = list(config["tasks"]["primary"])
    auxiliary_tasks = list(config["tasks"]["auxiliary"])
    required = {
        "molecule_id",
        "canonical_smiles",
        "split",
        "is_natural_product",
        *primary_tasks,
        *auxiliary_tasks,
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"model table missing columns: {sorted(missing)}")
    encoder = FingerprintEncoder(
        FingerprintConfig(n_bits=int(config["model"]["input_dim"]), backend="auto")
    )
    features_np = np.asarray(
        encoder.transform(frame["canonical_smiles"].tolist()), dtype=np.float32
    )
    labels_np = {
        task: frame[task].to_numpy(dtype=np.float32) for task in primary_tasks + auxiliary_tasks
    }
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    all_results, all_predictions = [], []
    families = list(config["training"]["model_families"])
    expanded_families = []
    for family in families:
        if family == "single_task":
            expanded_families.extend(f"single_task:{task}" for task in primary_tasks)
        else:
            expanded_families.append(family)
    for seed in config["seeds"]:
        for family in expanded_families:
            aux_weights = (
                [value for value in config["training"]["aux_loss_weights"] if value > 0]
                if family in {"naive_broadcast", "mil_aux", "permuted_mil"}
                else [0.0]
            )
            importance_options = (
                config["training"]["importance_weighting"] if family != "permuted_mil" else [False]
            )
            for aux_weight in aux_weights:
                for use_importance in importance_options:
                    print(
                        f"run family={family} seed={seed} aux={aux_weight} iw={use_importance}",
                        flush=True,
                    )
                    results, predictions, _ = train_one(
                        features_np=features_np,
                        labels_np=labels_np,
                        frame=frame,
                        primary_tasks=primary_tasks,
                        auxiliary_tasks=auxiliary_tasks,
                        pu_priors=dict(config["tasks"]["pu_priors"]),
                        bags=bags,
                        bag_membership=bag_membership,
                        family=family,
                        aux_weight=float(aux_weight),
                        use_importance=bool(use_importance),
                        seed=int(seed),
                        config=config,
                        device=device,
                    )
                    all_results.extend(results)
                    all_predictions.append(predictions)
                    pd.DataFrame(all_results).to_csv(output_dir / "metrics.csv", index=False)
                    pd.concat(all_predictions, ignore_index=True).to_parquet(
                        output_dir / "predictions.parquet", index=False
                    )
    dataset_manifest = json.loads((dataset_dir / "manifest.json").read_text())
    manifest = {
        "experiment": config["experiment_name"],
        "finished_at": datetime.now(UTC).isoformat(),
        "config_sha256": config_hash(args.config),
        "device": str(device),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "fingerprint_backend": encoder.backend,
        "rows": len(frame),
        "synthetic": bool(dataset_manifest.get("synthetic", False)),
        "confirmatory_eligible": bool(dataset_manifest.get("confirmatory_eligible", False)),
        "scientific_results": not bool(dataset_manifest.get("synthetic", False)),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

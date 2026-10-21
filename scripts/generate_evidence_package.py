#!/usr/bin/env python3
"""Generate manuscript figures, tables, statistics, and an artifact manifest."""

from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import time
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from vietherb_mtl import benjamini_hochberg, reliability_bins
from vietherb_mtl.evidence import RunFiles, archived_run, sha256


def directory_run(path: Path) -> RunFiles:
    return RunFiles(
        metrics=path / "metrics.csv",
        predictions=path / "predictions.parquet",
        manifest=path / "manifest.json",
    )


def normalized_family(value: str) -> str:
    if value.startswith("single_task:"):
        return "single_task_mlp"
    return value


DISPLAY = {
    "single_task_mlp": "Separate MLPs",
    "shared_primary": "Shared MLP",
    "logistic_regression": "Logistic regression",
    "extra_trees": "Extra Trees",
    "chemprop_dmpnn": "Chemprop D-MPNN",
    "shared_continuous": "Shared MLP",
}


def load_run(files: RunFiles) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    missing = [str(path) for path in files.inputs if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"run artifacts are missing: {missing}")
    metrics = pd.read_csv(files.metrics)
    predictions = pd.read_parquet(files.predictions)
    metrics["family"] = metrics["family"].map(normalized_family)
    predictions["family"] = predictions["family"].map(normalized_family)
    manifest = json.loads(files.manifest.read_text(encoding="utf-8"))
    if manifest.get("synthetic") or not manifest.get("scientific_results", True):
        raise RuntimeError(f"refusing scientific evidence from synthetic run: {files.manifest}")
    return metrics, predictions, manifest


def save_figure(figure: plt.Figure, stem: Path) -> list[Path]:
    paths = [stem.with_suffix(".pdf"), stem.with_suffix(".png")]
    fixed_date = datetime(2026, 10, 21, tzinfo=UTC)
    figure.savefig(
        paths[0],
        bbox_inches="tight",
        metadata={
            "Creator": "VietHerb-MTL",
            "CreationDate": fixed_date,
            "ModDate": fixed_date,
        },
    )
    figure.savefig(
        paths[1],
        dpi=300,
        bbox_inches="tight",
        metadata={"Software": "VietHerb-MTL"},
    )
    plt.close(figure)
    return paths


def macro_by_seed(metrics: pd.DataFrame, metric: str) -> pd.DataFrame:
    return metrics.groupby(["family", "seed"], as_index=False)[metric].mean()


def plot_data_flow(dataset_source: Path, out: Path) -> list[Path]:
    manifest_path = dataset_source if dataset_source.is_file() else dataset_source / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    extraction = manifest["chembl_source_manifests"][0]
    boxes = [
        ("ChEMBL 37", f"{extraction['candidate_rows']:,} candidate rows"),
        ("Assay curation", f"{extraction['rows']:,} eligible rows"),
        ("Pair curation", f"{manifest['curated_activity_pairs']:,} labelled pairs"),
        ("Chemical-OOD split", f"{manifest['molecules']:,} molecules"),
        ("Five-seed models", "classical, MLP, D-MPNN"),
        ("Evaluation", "ranking + calibration"),
    ]
    figure, axis = plt.subplots(figsize=(11.2, 3.0))
    axis.set_xlim(-0.5, len(boxes) - 0.5)
    axis.set_ylim(-0.9, 1.1)
    axis.axis("off")
    for index, (title, subtitle) in enumerate(boxes):
        axis.text(
            index,
            0.35,
            f"{title}\n{subtitle}",
            ha="center",
            va="center",
            fontsize=9,
            bbox={"boxstyle": "round,pad=0.45", "facecolor": "#e8f1f8", "edgecolor": "#277da1"},
        )
        if index < len(boxes) - 1:
            axis.annotate(
                "",
                xy=(index + 0.66, 0.35),
                xytext=(index + 0.34, 0.35),
                arrowprops={"arrowstyle": "->", "color": "#555555", "linewidth": 1.3},
            )
    axis.text(
        2.5,
        -0.52,
        "VietHerb permission + reviewer-audited mappings pending: MIL branch remains locked",
        ha="center",
        va="center",
        fontsize=9,
        color="#9c3d10",
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "#fff1e6", "edgecolor": "#f3722c"},
    )
    axis.annotate(
        "",
        xy=(4.0, 0.02),
        xytext=(3.0, -0.38),
        arrowprops={"arrowstyle": "-|>", "linestyle": "--", "color": "#f3722c"},
    )
    figure.tight_layout()
    return save_figure(figure, out / "fig1_workflow")


def plot_primary(metrics: pd.DataFrame, out: Path) -> list[Path]:
    macro = macro_by_seed(metrics, "pr_auc")
    summary = macro.groupby("family")["pr_auc"].agg(["mean", "std"]).sort_values("mean")
    figure, axis = plt.subplots(figsize=(6.6, 3.5))
    labels = [DISPLAY.get(item, item) for item in summary.index]
    positions = np.arange(len(summary))
    axis.errorbar(
        summary["mean"],
        positions,
        xerr=summary["std"],
        fmt="o",
        color="#277da1",
        capsize=3,
        markersize=7,
    )
    axis.set_yticks(positions, labels)
    axis.set_xlabel("Macro PR-AUC (mean ± SD, five seeds)")
    axis.set_xlim(max(0, float(summary["mean"].min()) - 0.08), 1.0)
    axis.grid(axis="x", alpha=0.25)
    figure.tight_layout()
    return save_figure(figure, out / "fig2_primary_macro_pr_auc")


def plot_targetwise(metrics: pd.DataFrame, out: Path) -> list[Path]:
    summary = metrics.groupby(["family", "task"])["pr_auc"].agg(["mean", "std"]).reset_index()
    families = list(summary.groupby("family")["mean"].mean().sort_values(ascending=False).index)
    tasks = ["activity_DPP4", "activity_ACHE", "activity_PTGS2"]
    figure, axis = plt.subplots(figsize=(7.2, 3.8))
    width = 0.8 / len(families)
    x = np.arange(len(tasks))
    for index, family in enumerate(families):
        subset = summary.set_index(["family", "task"]).loc[family]
        axis.bar(
            x - 0.4 + width / 2 + index * width,
            [subset.loc[task, "mean"] for task in tasks],
            width,
            yerr=[subset.loc[task, "std"] for task in tasks],
            capsize=2,
            label=DISPLAY.get(family, family),
        )
    axis.set_xticks(x, [task.replace("activity_", "") for task in tasks])
    axis.set_ylabel("PR-AUC")
    axis.set_ylim(0, 1.03)
    axis.grid(axis="y", alpha=0.25)
    axis.legend(frameon=False, ncol=2, fontsize=8)
    figure.tight_layout()
    return save_figure(figure, out / "fig3_target_pr_auc")


def plot_reliability(
    predictions: pd.DataFrame, out: Path
) -> tuple[list[Path], pd.DataFrame]:
    preferred = ("single_task_mlp", "shared_primary", "extra_trees", "chemprop_dmpnn")
    families = [item for item in preferred if item in set(predictions["family"])]
    tasks = ["activity_DPP4", "activity_ACHE", "activity_PTGS2"]
    figure, axes = plt.subplots(1, 3, figsize=(10.5, 3.2), sharex=True, sharey=True)
    records = []
    for axis, task in zip(axes, tasks, strict=True):
        for family in families:
            subset = predictions[
                (predictions["task"] == task) & (predictions["family"] == family)
            ]
            averaged = subset.groupby("molecule_id", as_index=False).agg(
                y_true=("y_true", "first"), y_score=("y_score", "mean")
            )
            bins = reliability_bins(averaged["y_true"], averaged["y_score"], n_bins=10)
            for row in bins:
                records.append({"family": family, "task": task, **row})
            occupied = [row for row in bins if row["count"]]
            axis.plot(
                [row["mean_probability"] for row in occupied],
                [row["observed_fraction"] for row in occupied],
                marker="o",
                linewidth=1.2,
                label=DISPLAY.get(family, family),
            )
        axis.plot([0, 1], [0, 1], linestyle="--", color="black", linewidth=0.8)
        axis.set_title(task.replace("activity_", ""))
        axis.grid(alpha=0.2)
    axes[0].set_ylabel("Observed active fraction")
    axes[1].set_xlabel("Mean predicted probability")
    axes[-1].legend(frameon=False, fontsize=7)
    figure.tight_layout()
    return save_figure(figure, out / "fig4_reliability"), pd.DataFrame(records)


def plot_enrichment(predictions: pd.DataFrame, out: Path) -> list[Path]:
    preferred = (
        "single_task_mlp",
        "shared_primary",
        "extra_trees",
        "logistic_regression",
        "chemprop_dmpnn",
    )
    families = [item for item in preferred if item in set(predictions["family"])]
    fractions = np.linspace(0.005, 0.10, 20)
    figure, axis = plt.subplots(figsize=(6.5, 3.8))
    for family in families:
        curves = []
        subset_family = predictions[predictions["family"] == family]
        for (_, task), rows in subset_family.groupby(["seed", "task"]):
            del task
            ordered = rows.sort_values("y_score", ascending=False)
            positives = max(float(ordered["y_true"].sum()), 1.0)
            curves.append(
                [
                    float(
                        ordered.iloc[: max(1, math.ceil(len(ordered) * fraction))][
                            "y_true"
                        ].sum()
                    )
                    / positives
                    for fraction in fractions
                ]
            )
        axis.plot(
            fractions * 100,
            np.mean(curves, axis=0),
            label=DISPLAY.get(family, family),
        )
    axis.set_xlabel("Test library screened (%)")
    axis.set_ylabel("Mean recall")
    axis.grid(alpha=0.25)
    axis.legend(frameon=False, fontsize=8)
    figure.tight_layout()
    return save_figure(figure, out / "fig5_early_enrichment")


def paired_target_bootstrap(
    predictions: pd.DataFrame,
    candidate: str = "shared_primary",
    reference: str = "single_task_mlp",
    replicates: int = 1000,
    seed: int = 20261020,
) -> pd.DataFrame:
    candidate_rows = predictions[predictions["family"] == candidate]
    reference_rows = predictions[predictions["family"] == reference]
    keys = ["seed", "task", "molecule_id", "component_id"]
    paired = candidate_rows.merge(
        reference_rows, on=keys, suffixes=("_candidate", "_reference"), validate="one_to_one"
    )
    paired = paired[
        np.isfinite(paired["y_true_candidate"])
        & np.isfinite(paired["y_true_reference"])
        & np.isfinite(paired["y_score_candidate"])
        & np.isfinite(paired["y_score_reference"])
    ].copy()
    if not np.array_equal(paired["y_true_candidate"], paired["y_true_reference"]):
        raise RuntimeError("candidate/reference labels do not match")
    rng = np.random.default_rng(seed)
    output = []
    for task, task_rows in paired.groupby("task"):
        observed_by_seed = []
        blocks = {}
        for model_seed, rows in task_rows.groupby("seed"):
            rows = rows.reset_index(drop=True)
            truth = rows["y_true_candidate"].to_numpy(dtype=int)
            candidate_score = rows["y_score_candidate"].to_numpy()
            reference_score = rows["y_score_reference"].to_numpy()
            observed_by_seed.append(
                average_precision_score(truth, candidate_score)
                - average_precision_score(truth, reference_score)
            )
            component_rows = [
                np.asarray(indices, dtype=int)
                for indices in rows.groupby("component_id", sort=False).indices.values()
            ]
            blocks[int(model_seed)] = (truth, candidate_score, reference_score, component_rows)
        seeds = np.asarray(sorted(blocks))
        draws = []
        for _ in range(replicates):
            deltas = []
            for model_seed in rng.choice(seeds, size=len(seeds), replace=True):
                truth, candidate_score, reference_score, component_rows = blocks[int(model_seed)]
                sampled = rng.integers(0, len(component_rows), size=len(component_rows))
                indices = np.concatenate([component_rows[index] for index in sampled])
                if len(np.unique(truth[indices])) < 2:
                    continue
                deltas.append(
                    average_precision_score(truth[indices], candidate_score[indices])
                    - average_precision_score(truth[indices], reference_score[indices])
                )
            if deltas:
                draws.append(float(np.mean(deltas)))
        values = np.asarray(draws)
        tail_probability = min(float((values <= 0).mean()), float((values >= 0).mean()))
        output.append(
            {
                "task": task,
                "observed_delta": float(np.mean(observed_by_seed)),
                "ci_low": float(np.quantile(values, 0.025)),
                "ci_high": float(np.quantile(values, 0.975)),
                "bootstrap_two_sided_p": min(1.0, 2 * tail_probability),
                "replicates": len(values),
            }
        )
    result = pd.DataFrame(output)
    result["bh_adjusted_p"] = benjamini_hochberg(result["bootstrap_two_sided_p"])
    return result


def natural_product_summary(
    predictions: pd.DataFrame, mapping_path: Path
) -> pd.DataFrame:
    mapping = pd.read_parquet(mapping_path)[["molecule_id", "is_natural_product"]]
    enriched = predictions.drop(columns="is_natural_product", errors="ignore").merge(
        mapping, on="molecule_id", how="left", validate="many_to_one"
    )
    enriched["is_natural_product"] = enriched["is_natural_product"].fillna(False)
    enriched = enriched[
        enriched["is_natural_product"]
        & np.isfinite(enriched["y_true"])
        & np.isfinite(enriched["y_score"])
    ]
    rows = []
    for (family, seed, task), subset in enriched.groupby(["family", "seed", "task"]):
        truth = subset["y_true"].to_numpy(dtype=int)
        if len(np.unique(truth)) < 2:
            pr_auc = math.nan
            roc_auc = math.nan
        else:
            pr_auc = float(average_precision_score(truth, subset["y_score"]))
            roc_auc = float(roc_auc_score(truth, subset["y_score"]))
        rows.append(
            {
                "family": family,
                "seed": seed,
                "task": task,
                "n": len(subset),
                "positives": int(truth.sum()),
                "negatives": int((truth == 0).sum()),
                "pr_auc": pr_auc,
                "roc_auc": roc_auc,
                "inferentially_eligible": bool(truth.sum() >= 30 and (truth == 0).sum() >= 30),
            }
        )
    return pd.DataFrame(rows)


def plot_sensitivity(
    temporal_metrics: pd.DataFrame | None,
    continuous_metrics: pd.DataFrame | None,
    out: Path,
) -> list[Path]:
    panels = int(temporal_metrics is not None) + int(continuous_metrics is not None)
    if not panels:
        return []
    figure, axes = plt.subplots(1, panels, figsize=(5.2 * panels, 3.5))
    axes_array = np.atleast_1d(axes)
    cursor = 0
    if temporal_metrics is not None:
        macro = macro_by_seed(temporal_metrics, "pr_auc")
        summary = macro.groupby("family")["pr_auc"].agg(["mean", "std"]).sort_values("mean")
        axes_array[cursor].barh(
            np.arange(len(summary)), summary["mean"], xerr=summary["std"], capsize=3
        )
        axes_array[cursor].set_yticks(
            np.arange(len(summary)), [DISPLAY.get(item, item) for item in summary.index]
        )
        axes_array[cursor].set_xlabel("Temporal macro PR-AUC")
        axes_array[cursor].grid(axis="x", alpha=0.25)
        cursor += 1
    if continuous_metrics is not None:
        macro = macro_by_seed(continuous_metrics, "mae")
        summary = macro.groupby("family")["mae"].agg(["mean", "std"]).sort_values("mean")
        axes_array[cursor].barh(
            np.arange(len(summary)), summary["mean"], xerr=summary["std"], capsize=3
        )
        axes_array[cursor].set_yticks(
            np.arange(len(summary)), [DISPLAY.get(item, item) for item in summary.index]
        )
        axes_array[cursor].set_xlabel("Continuous pChEMBL MAE (lower is better)")
        axes_array[cursor].grid(axis="x", alpha=0.25)
    figure.tight_layout()
    return save_figure(figure, out / "fig6_sensitivity")


def main() -> None:
    started_at = time.perf_counter()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--archive-dir",
        type=Path,
        help="Regenerate all evidence directly from the flat docs/manifests archive.",
    )
    parser.add_argument("--primary-neural", type=Path)
    parser.add_argument("--primary-classical", type=Path)
    parser.add_argument("--primary-extra", type=Path, nargs="*", default=[])
    parser.add_argument("--dataset-dir", type=Path)
    parser.add_argument("--temporal-neural", type=Path)
    parser.add_argument("--temporal-classical", type=Path)
    parser.add_argument("--continuous", type=Path)
    parser.add_argument("--natural-product-mapping", type=Path)
    parser.add_argument("--out", type=Path, default=Path("docs/evidence"))
    parser.add_argument(
        "--verify-reference",
        type=Path,
        help="Fail unless regenerated artifacts match this evidence directory's manifest.",
    )
    args = parser.parse_args()

    if args.archive_dir:
        conflicting = [
            args.primary_neural,
            args.primary_classical,
            *args.primary_extra,
            args.dataset_dir,
            args.temporal_neural,
            args.temporal_classical,
            args.continuous,
            args.natural_product_mapping,
        ]
        if any(item is not None for item in conflicting):
            parser.error("--archive-dir cannot be combined with individual run paths")
        archive = args.archive_dir
        primary_neural = archived_run(archive, "chembl37_activity")
        primary_classical = archived_run(archive, "chembl37_classical")
        primary_extra = [archived_run(archive, "chembl37_dmpnn")]
        temporal_neural = archived_run(archive, "chembl37_temporal_neural")
        temporal_classical = archived_run(archive, "chembl37_temporal_classical")
        continuous = archived_run(archive, "chembl37_continuous")
        dataset_source = archive / "chembl37_dataset_manifest.json"
        natural_product_mapping = archive / "chembl37_natural_product_mapping.parquet"
    else:
        required = {
            "--primary-neural": args.primary_neural,
            "--primary-classical": args.primary_classical,
            "--dataset-dir": args.dataset_dir,
        }
        missing = [name for name, value in required.items() if value is None]
        if missing:
            parser.error(f"required without --archive-dir: {', '.join(missing)}")
        primary_neural = directory_run(args.primary_neural)
        primary_classical = directory_run(args.primary_classical)
        primary_extra = [directory_run(path) for path in args.primary_extra]
        temporal_neural = directory_run(args.temporal_neural) if args.temporal_neural else None
        temporal_classical = (
            directory_run(args.temporal_classical) if args.temporal_classical else None
        )
        continuous = directory_run(args.continuous) if args.continuous else None
        dataset_source = args.dataset_dir
        natural_product_mapping = args.natural_product_mapping

    figures_dir = args.out / "figures"
    tables_dir = args.out / "tables"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    neural_metrics, neural_predictions, _ = load_run(primary_neural)
    classical_metrics, classical_predictions, _ = load_run(primary_classical)
    metric_frames = [neural_metrics, classical_metrics]
    prediction_frames = [neural_predictions, classical_predictions]
    for files in primary_extra:
        extra_metrics, extra_predictions, _ = load_run(files)
        metric_frames.append(extra_metrics)
        prediction_frames.append(extra_predictions)
    primary_metrics = pd.concat(metric_frames, ignore_index=True)
    primary_predictions = pd.concat(prediction_frames, ignore_index=True)
    generated: list[Path] = []
    generated.extend(plot_data_flow(dataset_source, figures_dir))
    generated.extend(plot_primary(primary_metrics, figures_dir))
    generated.extend(plot_targetwise(primary_metrics, figures_dir))
    reliability_paths, reliability = plot_reliability(primary_predictions, figures_dir)
    generated.extend(reliability_paths)
    generated.extend(plot_enrichment(primary_predictions, figures_dir))

    summary = primary_metrics.groupby(["family", "task"]).agg(
        n=("n", "first"),
        pr_auc_mean=("pr_auc", "mean"),
        pr_auc_sd=("pr_auc", "std"),
        bedroc20_mean=("bedroc20", "mean"),
        ef1_mean=("ef1", "mean"),
        ef5_mean=("ef5", "mean"),
        roc_auc_mean=("roc_auc", "mean"),
        brier_mean=("brier", "mean"),
        ece10_mean=("ece10", "mean"),
    ).reset_index()
    summary_path = tables_dir / "table_primary_metrics.csv"
    summary.to_csv(summary_path, index=False)
    generated.append(summary_path)
    reliability_path = tables_dir / "table_reliability_bins.csv"
    reliability.to_csv(reliability_path, index=False)
    generated.append(reliability_path)
    target_statistics = paired_target_bootstrap(primary_predictions)
    target_path = tables_dir / "table_target_bootstrap_bh.csv"
    target_statistics.to_csv(target_path, index=False)
    generated.append(target_path)
    if natural_product_mapping:
        natural = natural_product_summary(primary_predictions, natural_product_mapping)
        natural_path = tables_dir / "table_natural_product_descriptive.csv"
        natural.to_csv(natural_path, index=False)
        generated.append(natural_path)

    temporal_metrics = None
    if temporal_neural and temporal_classical:
        temporal_neural_metrics, _, _ = load_run(temporal_neural)
        temporal_classical_metrics, _, _ = load_run(temporal_classical)
        temporal_metrics = pd.concat(
            [temporal_neural_metrics, temporal_classical_metrics], ignore_index=True
        )
        temporal_path = tables_dir / "table_temporal_metrics.csv"
        temporal_metrics.to_csv(temporal_path, index=False)
        generated.append(temporal_path)
    continuous_metrics = None
    if continuous:
        continuous_metrics, _, _ = load_run(continuous)
        continuous_path = tables_dir / "table_continuous_metrics.csv"
        continuous_metrics.to_csv(continuous_path, index=False)
        generated.append(continuous_path)
    generated.extend(plot_sensitivity(temporal_metrics, continuous_metrics, figures_dir))

    run_inputs = [primary_neural, primary_classical, *primary_extra]
    run_inputs.extend(files for files in (temporal_neural, temporal_classical, continuous) if files)
    input_paths = [dataset_source]
    for files in run_inputs:
        input_paths.extend(files.inputs)
    if natural_product_mapping:
        input_paths.append(natural_product_mapping)
    input_paths = list(dict.fromkeys(input_paths))
    artifact_hashes = {path.relative_to(args.out).as_posix(): sha256(path) for path in generated}
    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "scientific_results": True,
        "runtime": {
            "wall_time_seconds": round(time.perf_counter() - started_at, 3),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "packages": {
                package: version(package)
                for package in ("matplotlib", "numpy", "pandas", "pyarrow", "scikit-learn")
            },
        },
        "inputs": {path.as_posix(): sha256(path) for path in input_paths},
        "artifacts": artifact_hashes,
    }
    manifest_path = args.out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if args.verify_reference:
        reference = json.loads(
            (args.verify_reference / "manifest.json").read_text(encoding="utf-8")
        )
        expected = reference["artifacts"]
        missing = sorted(set(expected) - set(artifact_hashes))
        unexpected = sorted(set(artifact_hashes) - set(expected))
        # Raster previews vary with platform font and image backends; PDFs and
        # machine-readable artifacts remain exact hash gates.
        mismatched = sorted(
            path
            for path in set(expected) & set(artifact_hashes)
            if not path.endswith(".png") and expected[path] != artifact_hashes[path]
        )
        if missing or unexpected or mismatched:
            raise SystemExit(
                "Evidence verification failed: "
                f"missing={missing}, unexpected={unexpected}, mismatched={mismatched}"
            )
        print(f"Verified {len(expected)} reproduced evidence artifacts")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

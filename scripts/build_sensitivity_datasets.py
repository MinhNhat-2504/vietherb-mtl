#!/usr/bin/env python3
"""Build continuous-potency and chronology-based ChEMBL 37 sensitivities."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from build_dataset import (
    AUXILIARY_COLUMNS,
    PRIMARY_COLUMNS,
    assign_components,
    component_ids,
    label_activity_pairs,
    read_chembl,
    stable_id,
    standardize,
)

POTENCY_COLUMNS = {
    "CHEMBL284": "potency_DPP4",
    "CHEMBL220": "potency_ACHE",
    "CHEMBL230": "potency_PTGS2",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_raw(config: dict) -> tuple[pd.DataFrame, str, list[dict], int]:
    raw, source_kind, source_manifests = read_chembl(Path(config["inputs"]["chembl_dir"]))
    raw = raw[raw["target_chembl_id"].isin(PRIMARY_COLUMNS)].copy()
    raw["pchembl_value"] = pd.to_numeric(raw["pchembl_value"], errors="coerce")
    raw = raw[raw["pchembl_value"].notna()]
    if "assay_type" in raw:
        raw = raw[raw["assay_type"].isin(config.get("retrieval", {}).get("assay_types", ["B"]))]
    if "potential_duplicate" in raw:
        duplicates = raw["potential_duplicate"].astype(str).str.lower().isin({"1", "true"})
        raw = raw[~duplicates]
    if "data_validity_comment" in raw:
        raw = raw[raw["data_validity_comment"].isna() | (raw["data_validity_comment"] == "")]
    if "standard_relation" in raw:
        allowed = set(config["activity"].get("allowed_relations", ["="]))
        raw = raw[raw["standard_relation"].isin(allowed)]

    standardized: dict[str, tuple[str, str, str]] = {}
    rejected = 0
    for smiles in raw["canonical_smiles"].dropna().unique():
        result = standardize(smiles)
        if result is None:
            rejected += 1
        else:
            standardized[smiles] = result
    raw = raw[raw["canonical_smiles"].isin(standardized)].copy()
    raw[["canonical_smiles_std", "inchikey", "murcko_scaffold"]] = (
        raw["canonical_smiles"].map(standardized).apply(pd.Series)
    )
    raw["molecule_id"] = raw["inchikey"].map(stable_id)
    return raw, source_kind, source_manifests, rejected


def aggregate_pairs(raw: pd.DataFrame, contradictory_margin: float) -> tuple[pd.DataFrame, int]:
    named_aggregations: dict[str, tuple[str, str]] = {
        "canonical_smiles": ("canonical_smiles_std", "first"),
        "inchikey": ("inchikey", "first"),
        "murcko_scaffold": ("murcko_scaffold", "first"),
        "pchembl_value": ("pchembl_value", "median"),
        "pchembl_min": ("pchembl_value", "min"),
        "pchembl_max": ("pchembl_value", "max"),
        "replicate_count": ("pchembl_value", "size"),
    }
    if "document_year" in raw:
        named_aggregations.update(
            {
                "first_document_year": ("document_year", "min"),
                "last_document_year": ("document_year", "max"),
            }
        )
    if "natural_product" in raw:
        named_aggregations["is_natural_product"] = ("natural_product", "max")
    aggregate = raw.groupby(["molecule_id", "target_chembl_id"], as_index=False).agg(
        **named_aggregations
    )
    aggregate["contradictory"] = (
        aggregate["pchembl_max"] - aggregate["pchembl_min"] >= contradictory_margin
    )
    contradictory = int(aggregate["contradictory"].sum())
    return aggregate[~aggregate["contradictory"]].copy(), contradictory


def identity_table(aggregate: pd.DataFrame) -> pd.DataFrame:
    aggregations = dict(
        canonical_smiles=("canonical_smiles", "first"),
        inchikey=("inchikey", "first"),
        murcko_scaffold=("murcko_scaffold", "first"),
    )
    if "is_natural_product" in aggregate:
        aggregations["is_natural_product"] = ("is_natural_product", "max")
    return aggregate.groupby("molecule_id", as_index=False).agg(**aggregations)


def add_common_columns(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    if "is_natural_product" not in result:
        result["is_natural_product"] = False
    else:
        result["is_natural_product"] = result["is_natural_product"].fillna(0).astype(bool)
    for column in AUXILIARY_COLUMNS:
        result[column] = 0.0
    return result


def write_dataset(
    output_dir: Path, table: pd.DataFrame, pairs: pd.DataFrame, manifest: dict
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    table_path = output_dir / "model_table.parquet"
    pairs_path = output_dir / "curated_activities.parquet"
    table.to_parquet(table_path, index=False)
    pairs.to_parquet(pairs_path, index=False)
    manifest["artifacts"] = {
        "model_table": {"path": table_path.name, "sha256": sha256(table_path)},
        "curated_activities": {"path": pairs_path.name, "sha256": sha256(pairs_path)},
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def build_continuous(
    raw: pd.DataFrame,
    config: dict,
    output_dir: Path,
    source_kind: str,
    source_manifests: list[dict],
    rejected: int,
) -> None:
    aggregate, contradictory = aggregate_pairs(
        raw, float(config["activity"]["contradictory_margin"])
    )
    identity = identity_table(aggregate)
    labels = aggregate.pivot(
        index="molecule_id", columns="target_chembl_id", values="pchembl_value"
    ).rename(columns=POTENCY_COLUMNS)
    table = add_common_columns(identity.merge(labels.reset_index(), on="molecule_id", how="left"))
    split_config = config["split"]
    components = component_ids(
        table,
        None,
        similarity_threshold=float(split_config["chemical_cluster_tanimoto"]),
        fingerprint_radius=int(config["features"]["radius"]),
        fingerprint_bits=int(config["features"]["n_bits"]),
    )
    table["component_id"] = table["molecule_id"].map(components)
    proxy = table.copy()
    for target_id, activity_column in PRIMARY_COLUMNS.items():
        proxy[activity_column] = (
            proxy[POTENCY_COLUMNS[target_id]] >= config["activity"]["active_threshold_pchembl"]
        ).where(proxy[POTENCY_COLUMNS[target_id]].notna())
    assignments = assign_components(
        proxy, list(split_config["fractions"]), int(split_config["seed"])
    )
    table["split"] = table["component_id"].map(assignments)
    manifest = {
        "built_at": datetime.now(UTC).isoformat(),
        "kind": "continuous_potency_sensitivity",
        "source_kind": source_kind,
        "confirmatory_eligible": source_kind == "pinned_sqlite_verified",
        "source_manifests": source_manifests,
        "contradictory_pairs_excluded": contradictory,
        "gray_zone_pairs_included": True,
        "rejected_unique_smiles": rejected,
        "molecules": len(table),
        "activity_pairs": len(aggregate),
        "split_counts": table["split"].value_counts().to_dict(),
        "split_policy": {
            "method": "chemical_cluster_components_continuous",
            "chemical_cluster_tanimoto": split_config["chemical_cluster_tanimoto"],
            "fractions": split_config["fractions"],
            "seed": split_config["seed"],
        },
    }
    write_dataset(output_dir, table, aggregate, manifest)


def build_temporal(
    raw: pd.DataFrame,
    config: dict,
    output_dir: Path,
    source_kind: str,
    source_manifests: list[dict],
    rejected: int,
    train_end_year: int,
    validation_end_year: int,
) -> None:
    temporal = raw.copy()
    temporal["document_year"] = pd.to_numeric(temporal["document_year"], errors="coerce")
    missing_year_rows = int(temporal["document_year"].isna().sum())
    temporal = temporal[temporal["document_year"].notna()].copy()
    temporal["document_year"] = temporal["document_year"].astype(int)
    first_year = temporal.groupby("molecule_id")["document_year"].min()
    temporal["first_document_year"] = temporal["molecule_id"].map(first_year)
    temporal["split"] = np.select(
        [
            temporal["first_document_year"] <= train_end_year,
            temporal["first_document_year"] <= validation_end_year,
        ],
        ["train", "validation"],
        default="test",
    )
    allowed_as_of = (
        ((temporal["split"] == "train") & (temporal["document_year"] <= train_end_year))
        | (
            (temporal["split"] == "validation")
            & (temporal["document_year"] <= validation_end_year)
        )
        | (temporal["split"] == "test")
    )
    future_rows_excluded = int((~allowed_as_of).sum())
    temporal = temporal[allowed_as_of].copy()
    aggregate, contradictory = aggregate_pairs(
        temporal, float(config["activity"]["contradictory_margin"])
    )
    aggregate, gray = label_activity_pairs(aggregate, config["activity"])
    identity = identity_table(aggregate)
    labels = aggregate.pivot(
        index="molecule_id", columns="target_chembl_id", values="active"
    ).rename(columns=PRIMARY_COLUMNS)
    table = add_common_columns(identity.merge(labels.reset_index(), on="molecule_id", how="left"))
    table["first_document_year"] = table["molecule_id"].map(first_year).astype(int)
    table["split"] = np.select(
        [
            table["first_document_year"] <= train_end_year,
            table["first_document_year"] <= validation_end_year,
        ],
        ["train", "validation"],
        default="test",
    )
    components = component_ids(
        table,
        None,
        similarity_threshold=float(config["split"]["chemical_cluster_tanimoto"]),
        fingerprint_radius=int(config["features"]["radius"]),
        fingerprint_bits=int(config["features"]["n_bits"]),
    )
    table["component_id"] = table["molecule_id"].map(components)
    manifest = {
        "built_at": datetime.now(UTC).isoformat(),
        "kind": "temporal_holdout_sensitivity",
        "source_kind": source_kind,
        "confirmatory_eligible": source_kind == "pinned_sqlite_verified",
        "source_manifests": source_manifests,
        "missing_document_year_rows_excluded": missing_year_rows,
        "post_cutoff_training_or_validation_rows_excluded": future_rows_excluded,
        "contradictory_pairs_excluded": contradictory,
        "gray_zone_pairs_excluded": gray,
        "rejected_unique_smiles": rejected,
        "molecules": len(table),
        "activity_pairs": len(aggregate),
        "split_counts": table["split"].value_counts().to_dict(),
        "split_policy": {
            "method": "first_document_year_temporal_holdout",
            "train_end_year": train_end_year,
            "validation_end_year": validation_end_year,
            "test_start_year": validation_end_year + 1,
            "future_label_censoring": True,
            "chemical_cluster_tanimoto": None,
        },
    }
    write_dataset(output_dir, table, aggregate, manifest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/dataset.yaml"))
    parser.add_argument("--continuous-out", type=Path, default=Path("data/processed/continuous_v1"))
    parser.add_argument("--temporal-out", type=Path, default=Path("data/processed/temporal_v1"))
    parser.add_argument("--train-end-year", type=int, default=2017)
    parser.add_argument("--validation-end-year", type=int, default=2021)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    for output in (args.continuous_out, args.temporal_out):
        if output.exists() and any(output.iterdir()) and not args.overwrite:
            raise FileExistsError(f"{output} is not empty; pass --overwrite explicitly")
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    raw, source_kind, source_manifests, rejected = prepare_raw(config)
    if source_kind != "pinned_sqlite_verified":
        raise RuntimeError("sensitivity datasets require a verified pinned SQLite extract")
    build_continuous(
        raw, config, args.continuous_out, source_kind, source_manifests, rejected
    )
    build_temporal(
        raw,
        config,
        args.temporal_out,
        source_kind,
        source_manifests,
        rejected,
        args.train_end_year,
        args.validation_end_year,
    )
    print(json.dumps({"continuous": str(args.continuous_out), "temporal": str(args.temporal_out)}))


if __name__ == "__main__":
    main()

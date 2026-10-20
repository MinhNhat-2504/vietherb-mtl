#!/usr/bin/env python3
"""Build the frozen molecule-level modelling table and leakage-safe splits."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from rdkit import Chem, rdBase
from rdkit.Chem.MolStandardize import rdMolStandardize
from rdkit.Chem.Scaffolds import MurckoScaffold

PRIMARY_COLUMNS = {
    "CHEMBL284": "activity_DPP4",
    "CHEMBL220": "activity_ACHE",
    "CHEMBL230": "activity_PTGS2",
}
AUXILIARY_COLUMNS = ("ethno_diabetes", "ethno_neuro", "ethno_inflammation")


def stable_id(inchikey: str) -> str:
    return "MOL_" + hashlib.sha256(inchikey.encode()).hexdigest()[:16]


def standardize(smiles: str) -> tuple[str, str, str] | None:
    molecule = Chem.MolFromSmiles(str(smiles))
    if molecule is None:
        return None
    molecule = rdMolStandardize.FragmentParent(molecule)
    molecule = rdMolStandardize.Normalizer().normalize(molecule)
    molecule = rdMolStandardize.Reionizer().reionize(molecule)
    molecule = rdMolStandardize.Uncharger().uncharge(molecule)
    molecule = rdMolStandardize.TautomerEnumerator().Canonicalize(molecule)
    smiles_out = Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True)
    inchikey = Chem.MolToInchiKey(molecule)
    scaffold_mol = MurckoScaffold.GetScaffoldForMol(molecule)
    scaffold = Chem.MolToSmiles(scaffold_mol, canonical=True)
    return smiles_out, inchikey, scaffold


def read_chembl(path: Path) -> tuple[pd.DataFrame, str]:
    parquet_files = sorted(path.glob("*.parquet"))
    if parquet_files:
        return pd.concat([pd.read_parquet(item) for item in parquet_files]), "pinned_sqlite"
    jsonl_files = sorted(path.glob("CHEMBL*.jsonl"))
    if not jsonl_files:
        raise FileNotFoundError(f"no ChEMBL parquet or target JSONL files found in {path}")
    records = []
    for filename in jsonl_files:
        with filename.open(encoding="utf-8") as stream:
            records.extend(json.loads(line) for line in stream if line.strip())
    return pd.DataFrame(records), "exploratory_live_api"


class DisjointSet:
    def __init__(self, items: list[str]) -> None:
        self.parent = {item: item for item in items}

    def find(self, item: str) -> str:
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        while item != root:
            parent = self.parent[item]
            self.parent[item] = root
            item = parent
        return root

    def union(self, left: str, right: str) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def component_ids(molecules: pd.DataFrame, species_edges: pd.DataFrame | None) -> dict[str, str]:
    ids = molecules["molecule_id"].tolist()
    dsu = DisjointSet(ids)
    for _, group in molecules.groupby("murcko_scaffold", sort=False):
        members = group["molecule_id"].tolist()
        for member in members[1:]:
            dsu.union(members[0], member)
    if species_edges is not None and not species_edges.empty:
        allowed = set(ids)
        for _, group in species_edges.groupby("species_id", sort=False):
            members = [item for item in group["molecule_id"].unique() if item in allowed]
            for member in members[1:]:
                dsu.union(members[0], member)
    roots = {item: dsu.find(item) for item in ids}
    root_names = {root: f"CC_{index:06d}" for index, root in enumerate(sorted(set(roots.values())))}
    return {item: root_names[root] for item, root in roots.items()}


def assign_components(frame: pd.DataFrame, fractions: list[float], seed: int) -> dict[str, str]:
    """Greedy multi-label balancing while never splitting a component."""

    names = ("train", "validation", "test")
    tasks = list(PRIMARY_COLUMNS.values())
    totals = np.array([len(frame), *[frame[column].fillna(0).sum() for column in tasks]])
    desired = {name: totals * fraction for name, fraction in zip(names, fractions, strict=True)}
    current = {name: np.zeros_like(totals, dtype=float) for name in names}
    groups = []
    for component, rows in frame.groupby("component_id"):
        vector = np.array([len(rows), *[rows[column].fillna(0).sum() for column in tasks]])
        groups.append((component, vector))
    random.Random(seed).shuffle(groups)
    groups.sort(key=lambda item: (item[1][0], item[1][1:].sum()), reverse=True)
    assignments = {}
    scale = np.maximum(totals, 1.0)
    for component, vector in groups:
        best = min(
            names,
            key=lambda name: (
                np.square((current[name] + vector - desired[name]) / scale).sum()
                - np.square((current[name] - desired[name]) / scale).sum()
            ),
        )
        assignments[component] = best
        current[best] += vector
    return assignments


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    inputs = config["inputs"]
    output_dir = Path(config["output_dir"])
    output_path = output_dir / "model_table.parquet"
    if output_path.exists() and not args.overwrite:
        raise FileExistsError(f"{output_path} exists; pass --overwrite explicitly")

    raw, chembl_kind = read_chembl(Path(inputs["chembl_dir"]))
    required = {"target_chembl_id", "canonical_smiles", "pchembl_value"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"ChEMBL input missing columns: {sorted(missing)}")
    raw = raw[raw["target_chembl_id"].isin(PRIMARY_COLUMNS)].copy()
    allowed_assay_types = set(config.get("retrieval", {}).get("assay_types", ["B"]))
    if "assay_type" in raw and allowed_assay_types:
        raw = raw[raw["assay_type"].isin(allowed_assay_types)]
    raw["pchembl_value"] = pd.to_numeric(raw["pchembl_value"], errors="coerce")
    raw = raw[raw["pchembl_value"].notna()]
    if "potential_duplicate" in raw:
        duplicate = raw["potential_duplicate"].astype(str).str.lower().isin({"1", "true"})
        raw = raw[~duplicate]
    if "data_validity_comment" in raw:
        raw = raw[raw["data_validity_comment"].isna() | (raw["data_validity_comment"] == "")]
    if "standard_relation" in raw:
        raw = raw[raw["standard_relation"].fillna("=").isin({"=", "<", "<=", None})]

    standardized = {}
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
    aggregate = raw.groupby(["molecule_id", "target_chembl_id"], as_index=False).agg(
        canonical_smiles=("canonical_smiles_std", "first"),
        inchikey=("inchikey", "first"),
        murcko_scaffold=("murcko_scaffold", "first"),
        pchembl_value=("pchembl_value", "median"),
        pchembl_min=("pchembl_value", "min"),
        pchembl_max=("pchembl_value", "max"),
        replicate_count=("pchembl_value", "size"),
    )
    aggregate["contradictory"] = (
        aggregate["pchembl_max"] - aggregate["pchembl_min"]
        >= config["activity"]["contradictory_margin"]
    )
    aggregate = aggregate[~aggregate["contradictory"]].copy()
    aggregate["active"] = (
        aggregate["pchembl_value"] >= config["activity"]["active_threshold_pchembl"]
    ).astype(float)
    identity = aggregate.groupby("molecule_id", as_index=False).agg(
        canonical_smiles=("canonical_smiles", "first"),
        inchikey=("inchikey", "first"),
        murcko_scaffold=("murcko_scaffold", "first"),
    )
    labels = aggregate.pivot(index="molecule_id", columns="target_chembl_id", values="active")
    labels = labels.rename(columns=PRIMARY_COLUMNS).reset_index()
    molecules = identity.merge(labels, on="molecule_id", how="left")
    molecules["is_natural_product"] = False
    for column in AUXILIARY_COLUMNS:
        molecules[column] = 0.0  # zero means unlabelled for nnPU, never a confirmed negative

    species_edges = None
    bags = None
    bag_membership = None
    vietherb_dir = Path(inputs["vietherb_dir"])
    mapping_path = Path(inputs["term_mapping"])
    if (vietherb_dir / "molecules.parquet").exists():
        vh_molecules = pd.read_parquet(vietherb_dir / "molecules.parquet")
        vh_edges = pd.read_parquet(vietherb_dir / "species_metabolites.parquet")
        vh_uses = pd.read_parquet(vietherb_dir / "species_uses.parquet")
        vh_molecules[["canonical_smiles", "inchikey", "murcko_scaffold"]] = (
            vh_molecules["canonical_smiles"].map(lambda value: standardize(value)).apply(pd.Series)
        )
        vh_molecules["molecule_id"] = vh_molecules["inchikey"].map(stable_id)
        species_edges = (
            vh_edges.drop(columns="molecule_id", errors="ignore")
            .merge(
                vh_molecules[["source_id", "molecule_id"]],
                left_on="metabolite_id",
                right_on="source_id",
                how="inner",
            )[["species_id", "molecule_id"]]
            .drop_duplicates()
        )
        for column in PRIMARY_COLUMNS.values():
            vh_molecules[column] = np.nan
        for column in AUXILIARY_COLUMNS:
            vh_molecules[column] = 0.0
        bag_membership = species_edges.rename(columns={"species_id": "bag_id"})[
            ["bag_id", "molecule_id"]
        ].drop_duplicates()
        bags = pd.DataFrame({"bag_id": sorted(bag_membership["bag_id"].unique())})
        for column in AUXILIARY_COLUMNS:
            bags[column] = 0.0  # unlabelled under the bag-level PU objective
        if mapping_path.exists() and mapping_path.stat().st_size > 0:
            mapping = pd.read_csv(mapping_path)
            mapping = mapping[mapping["auxiliary_task"].isin(AUXILIARY_COLUMNS)]
            mapping["raw_use_normalized"] = (
                mapping["raw_use_normalized"].astype(str).str.casefold().str.strip()
            )
            vh_uses["raw_use_normalized"] = (
                vh_uses["raw_use"].astype(str).str.casefold().str.strip()
            )
            positive_bags = (
                vh_uses.merge(
                    mapping[["raw_use_normalized", "auxiliary_task"]], on="raw_use_normalized"
                )
                .rename(columns={"species_id": "bag_id"})[["bag_id", "auxiliary_task"]]
                .drop_duplicates()
            )
            for task in AUXILIARY_COLUMNS:
                positive_bag_ids = set(
                    positive_bags.loc[positive_bags["auxiliary_task"] == task, "bag_id"]
                )
                bags[task] = bags["bag_id"].isin(positive_bag_ids).astype(float)
                # Kept only for the explicitly named naive-broadcast ablation.
                positive_ids = set(
                    bag_membership.loc[
                        bag_membership["bag_id"].isin(positive_bag_ids), "molecule_id"
                    ]
                )
                vh_molecules[task] = vh_molecules["molecule_id"].isin(positive_ids).astype(float)
        keep = [
            "molecule_id",
            "canonical_smiles",
            "inchikey",
            "murcko_scaffold",
            "is_natural_product",
            *PRIMARY_COLUMNS.values(),
            *AUXILIARY_COLUMNS,
        ]
        molecules = pd.concat([molecules, vh_molecules[keep]], ignore_index=True)
        aggregations = {
            "canonical_smiles": "first",
            "inchikey": "first",
            "murcko_scaffold": "first",
            "is_natural_product": "max",
            **{column: "max" for column in PRIMARY_COLUMNS.values()},
            **{column: "max" for column in AUXILIARY_COLUMNS},
        }
        molecules = molecules.groupby("molecule_id", as_index=False).agg(aggregations)

    components = component_ids(molecules, species_edges)
    molecules["component_id"] = molecules["molecule_id"].map(components)
    split_config = config["split"]
    assignments = assign_components(
        molecules, list(split_config["fractions"]), int(split_config["seed"])
    )
    molecules["split"] = molecules["component_id"].map(assignments)
    output_dir.mkdir(parents=True, exist_ok=True)
    molecules.to_parquet(output_path, index=False)
    aggregate.to_parquet(output_dir / "curated_activities.parquet", index=False)
    if bags is not None and bag_membership is not None:
        molecule_splits = molecules.set_index("molecule_id")["split"]
        bag_membership["split"] = bag_membership["molecule_id"].map(molecule_splits)
        split_cardinality = bag_membership.groupby("bag_id")["split"].nunique()
        if bool((split_cardinality != 1).any()):
            raise RuntimeError("species bag crosses molecule splits")
        bag_splits = bag_membership.groupby("bag_id")["split"].first()
        bags["split"] = bags["bag_id"].map(bag_splits)
        bags.to_parquet(output_dir / "bags.parquet", index=False)
        bag_membership.to_parquet(output_dir / "bag_membership.parquet", index=False)
    summary = {
        "built_at": datetime.now(UTC).isoformat(),
        "chembl_input_kind": chembl_kind,
        "confirmatory_eligible": chembl_kind == "pinned_sqlite",
        "rdkit_version": rdBase.rdkitVersion,
        "raw_activity_rows": len(raw),
        "curated_activity_pairs": len(aggregate),
        "molecules": len(molecules),
        "herb_bags": 0 if bags is None else len(bags),
        "rejected_unique_smiles": rejected,
        "split_counts": molecules["split"].value_counts().to_dict(),
        "target_positive_counts": {
            column: int(molecules[column].fillna(0).sum()) for column in PRIMARY_COLUMNS.values()
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

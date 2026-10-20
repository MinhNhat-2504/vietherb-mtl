#!/usr/bin/env python3
"""Validate and standardize an authorized VietHerb tabular export."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from rdkit import Chem, rdBase
from rdkit.Chem.MolStandardize import rdMolStandardize

REQUIRED = {
    "species.csv": {"species_id", "scientific_name"},
    "metabolites.csv": {"metabolite_id", "name", "smiles"},
    "species_metabolites.csv": {"species_id", "metabolite_id"},
    "species_uses.csv": {"species_id", "raw_use"},
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def standardize(smiles: str) -> tuple[str, str] | None:
    molecule = Chem.MolFromSmiles(str(smiles))
    if molecule is None:
        return None
    molecule = rdMolStandardize.FragmentParent(molecule)
    molecule = rdMolStandardize.Normalizer().normalize(molecule)
    molecule = rdMolStandardize.Reionizer().reionize(molecule)
    molecule = rdMolStandardize.Uncharger().uncharge(molecule)
    molecule = rdMolStandardize.TautomerEnumerator().Canonicalize(molecule)
    canonical = Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True)
    return canonical, Chem.MolToInchiKey(molecule)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    tables: dict[str, pd.DataFrame] = {}
    source_manifest = {}
    for filename, columns in REQUIRED.items():
        path = args.input / filename
        if not path.exists():
            raise FileNotFoundError(f"required VietHerb export table missing: {path}")
        table = pd.read_csv(path)
        missing = columns - set(table.columns)
        if missing:
            raise ValueError(f"{filename} missing columns: {sorted(missing)}")
        tables[filename] = table
        source_manifest[filename] = {"rows": len(table), "sha256": digest(path)}

    species = tables["species.csv"].copy()
    metabolites = tables["metabolites.csv"].copy()
    edges = tables["species_metabolites.csv"].copy()
    uses = tables["species_uses.csv"].copy()
    if species["species_id"].duplicated().any():
        raise ValueError("species_id must be unique in species.csv")
    if metabolites["metabolite_id"].duplicated().any():
        raise ValueError("metabolite_id must be unique in metabolites.csv")
    if not set(edges["species_id"]).issubset(set(species["species_id"])):
        raise ValueError("species_metabolites contains unknown species_id")
    if not set(edges["metabolite_id"]).issubset(set(metabolites["metabolite_id"])):
        raise ValueError("species_metabolites contains unknown metabolite_id")
    if not set(uses["species_id"]).issubset(set(species["species_id"])):
        raise ValueError("species_uses contains unknown species_id")

    accepted, rejected = [], []
    for row in metabolites.itertuples(index=False):
        result = standardize(row.smiles)
        if result is None:
            rejected.append({"metabolite_id": row.metabolite_id, "reason": "invalid_smiles"})
            continue
        smiles, inchikey = result
        accepted.append(
            {
                "metabolite_id": row.metabolite_id,
                "name": row.name,
                "canonical_smiles": smiles,
                "inchikey": inchikey,
                "molecule_id": "MOL_" + hashlib.sha256(inchikey.encode()).hexdigest()[:16],
                "source": "vietherb",
                "source_id": row.metabolite_id,
                "is_natural_product": True,
            }
        )
    molecules = pd.DataFrame(accepted)
    if molecules.empty:
        raise ValueError("no valid VietHerb structures remained after standardization")
    molecule_lookup = molecules[["metabolite_id", "molecule_id"]]
    standardized_edges = edges.merge(molecule_lookup, on="metabolite_id", how="inner")
    outputs = {
        "molecules.parquet": molecules.drop(columns=["metabolite_id"]),
        "species_metabolites.parquet": standardized_edges,
        "species_uses.parquet": uses,
        "species.parquet": species,
    }
    for filename, table in outputs.items():
        path = args.out / filename
        if path.exists() and not args.overwrite:
            raise FileExistsError(f"{path} exists; pass --overwrite explicitly")
        table.to_parquet(path, index=False)
    pd.DataFrame(rejected, columns=["metabolite_id", "reason"]).to_csv(
        args.out / "rejected_structures.csv", index=False
    )
    manifest = {
        "kind": "authorized_vietherb_export",
        "processed_at": datetime.now(UTC).isoformat(),
        "rdkit_version": rdBase.rdkitVersion,
        "sources": source_manifest,
        "accepted_structures": len(molecules),
        "rejected_structures": len(rejected),
        "license_note": "Record the permission/license for the supplied export here.",
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"accepted": len(molecules), "rejected": len(rejected)}, indent=2))


if __name__ == "__main__":
    main()

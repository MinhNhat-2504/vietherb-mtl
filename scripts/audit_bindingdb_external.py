#!/usr/bin/env python3
"""Audit a document- and chemistry-disjoint BindingDB external cohort."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs, rdBase
from rdkit.Chem import rdFingerprintGenerator
from rdkit.Chem.MolStandardize import rdMolStandardize

from vietherb_mtl.external import strict_affinity

TARGETS = {
    "P27487": "activity_DPP4",
    "P22303": "activity_ACHE",
    "P35354": "activity_PTGS2",
}
SOURCE_URL = (
    "https://www.bindingdb.org/rwd/bind/downloads/"
    "BindingDB_BindingDB_Articles_202610_tsv.zip"
)
SOURCE_MD5 = "4b1d2f7c90e83dc6fd13e7b106a1f545"
SOURCE_SHA256 = "727383bac35beed6bc5c55c40dfbd58ba023fa97a7f27dc1a61440c1ad54a2b7"
TARGET_COLUMN = "UniProt (SwissProt) Primary ID of Target Chain 1"
CHAIN_COLUMN = "Number of Protein Chains in Target (>1 implies a multichain complex)"
ORGANISM_COLUMN = "Target Source Organism According to Curator or DataSource"
USE_COLUMNS = (
    "BindingDB Reactant_set_id",
    "Ligand SMILES",
    "Ligand InChI Key",
    "Target Name",
    ORGANISM_COLUMN,
    "Ki (nM)",
    "IC50 (nM)",
    "Article DOI",
    "PMID",
    "Date of publication",
    "Curation/DataSource",
    CHAIN_COLUMN,
    TARGET_COLUMN,
)


def file_hash(path: Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def standardize(smiles: str) -> tuple[str, str] | None:
    molecule = Chem.MolFromSmiles(str(smiles))
    if molecule is None:
        return None
    try:
        molecule = rdMolStandardize.FragmentParent(molecule)
        molecule = rdMolStandardize.Normalizer().normalize(molecule)
        molecule = rdMolStandardize.Reionizer().reionize(molecule)
        molecule = rdMolStandardize.Uncharger().uncharge(molecule)
        molecule = rdMolStandardize.TautomerEnumerator().Canonicalize(molecule)
    except (RuntimeError, ValueError):
        return None
    canonical = Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True)
    return canonical, Chem.MolToInchiKey(molecule)


def counts_by_target_label(frame: pd.DataFrame) -> dict[str, dict[str, int]]:
    output = {}
    for accession, task in TARGETS.items():
        rows = frame[frame[TARGET_COLUMN] == accession]
        output[task] = {
            "inactive": int((rows["label"] == 0).sum()),
            "active": int((rows["label"] == 1).sum()),
            "total": int(len(rows)),
        }
    return output


def read_target_rows(path: Path) -> pd.DataFrame:
    frames = []
    for chunk in pd.read_csv(
        path,
        sep="\t",
        usecols=list(USE_COLUMNS),
        dtype=str,
        chunksize=50_000,
        low_memory=False,
    ):
        selected = chunk[chunk[TARGET_COLUMN].isin(TARGETS)].copy()
        if not selected.empty:
            frames.append(selected)
    if not frames:
        raise RuntimeError("BindingDB snapshot contains no rows for the prespecified targets")
    return pd.concat(frames, ignore_index=True)


def build_measurements(frame: pd.DataFrame) -> pd.DataFrame:
    long_frames = []
    for column, endpoint in (("Ki (nM)", "Ki"), ("IC50 (nM)", "IC50")):
        selected = frame.copy()
        selected["value_nm"] = selected[column].map(strict_affinity)
        selected = selected[selected["value_nm"].notna()].copy()
        selected["endpoint"] = endpoint
        selected["pchembl"] = 9.0 - np.log10(selected["value_nm"].astype(float))
        selected["label"] = np.select(
            [selected["pchembl"] >= 6.0, selected["pchembl"] <= 5.0],
            [1.0, 0.0],
            default=np.nan,
        )
        long_frames.append(selected[selected["label"].notna()])
    return pd.concat(long_frames, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bindingdb-tsv", type=Path, required=True)
    parser.add_argument("--bindingdb-zip", type=Path, required=True)
    parser.add_argument("--chembl-activities", type=Path, required=True)
    parser.add_argument("--chembl-model-table", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--similarity-cutoff", type=float, default=0.70)
    parser.add_argument("--minimum-class-count", type=int, default=30)
    args = parser.parse_args()

    if not 0 < args.similarity_cutoff <= 1:
        parser.error("--similarity-cutoff must be in (0, 1]")
    args.out.mkdir(parents=True, exist_ok=True)
    source_md5 = file_hash(args.bindingdb_zip, "md5")
    source_sha256 = file_hash(args.bindingdb_zip)
    if source_md5 != SOURCE_MD5 or source_sha256 != SOURCE_SHA256:
        raise RuntimeError("BindingDB snapshot checksum mismatch")

    rows = read_target_rows(args.bindingdb_tsv)
    stage_counts: dict[str, int] = {"matched_target_rows": int(len(rows))}
    rows = rows[
        rows[ORGANISM_COLUMN].isin(("Homo sapiens", "Human"))
        & pd.to_numeric(rows[CHAIN_COLUMN], errors="coerce").eq(1)
        & rows["Curation/DataSource"].eq("Curated from the literature by BindingDB")
    ].copy()
    stage_counts["single_chain_human_article_rows"] = int(len(rows))

    chembl_documents = pd.read_parquet(
        args.chembl_activities, columns=["doi", "pubmed_id"]
    )
    chembl_dois = set(
        chembl_documents["doi"].dropna().astype(str).str.lower().str.strip()
    )
    chembl_pmids = set(
        chembl_documents["pubmed_id"].dropna().astype(float).astype(int).astype(str)
    )
    doi = rows["Article DOI"].fillna("").str.lower().str.strip()
    pmid = rows["PMID"].fillna("").str.replace(r"\.0$", "", regex=True).str.strip()
    rows["has_document_id"] = doi.ne("") | pmid.ne("")
    rows["document_overlap"] = doi.isin(chembl_dois) | pmid.isin(chembl_pmids)
    measurements = build_measurements(rows)
    stage_counts["strict_binary_measurements"] = int(len(measurements))
    measurements = measurements[
        measurements["has_document_id"] & ~measurements["document_overlap"]
    ].copy()
    stage_counts["document_disjoint_measurements"] = int(len(measurements))

    standardized = {
        smiles: standardize(smiles) for smiles in measurements["Ligand SMILES"].unique()
    }
    measurements["standardized"] = measurements["Ligand SMILES"].map(standardized)
    stage_counts["invalid_structure_measurements"] = int(
        measurements["standardized"].isna().sum()
    )
    measurements = measurements[measurements["standardized"].notna()].copy()
    measurements["canonical_smiles"] = measurements["standardized"].map(lambda item: item[0])
    measurements["inchikey"] = measurements["standardized"].map(lambda item: item[1])

    pairs = (
        measurements.groupby(["inchikey", "canonical_smiles", TARGET_COLUMN], as_index=False)
        .agg(
            label_min=("label", "min"),
            label_max=("label", "max"),
            pchembl_value=("pchembl", "median"),
            measurement_count=("label", "size"),
            article_doi=("Article DOI", "first"),
            pubmed_id=("PMID", "first"),
        )
    )
    stage_counts["document_disjoint_pairs_before_contradictions"] = int(len(pairs))
    stage_counts["contradictory_pairs_excluded"] = int(
        pairs["label_min"].ne(pairs["label_max"]).sum()
    )
    pairs = pairs[pairs["label_min"].eq(pairs["label_max"])].copy()
    pairs["label"] = pairs["label_min"].astype(int)

    model = pd.read_parquet(
        args.chembl_model_table, columns=["canonical_smiles", "inchikey"]
    )
    model_inchikeys = set(model["inchikey"])
    stage_counts["exact_molecule_overlap_excluded"] = int(
        pairs["inchikey"].isin(model_inchikeys).sum()
    )
    pairs = pairs[~pairs["inchikey"].isin(model_inchikeys)].copy()

    generator = rdFingerprintGenerator.GetMorganGenerator(
        radius=2, fpSize=2048, includeChirality=True
    )
    cohort_fingerprints = [
        generator.GetFingerprint(Chem.MolFromSmiles(smiles))
        for smiles in model["canonical_smiles"]
    ]

    def maximum_similarity(smiles: str) -> float:
        fingerprint = generator.GetFingerprint(Chem.MolFromSmiles(smiles))
        return float(max(DataStructs.BulkTanimotoSimilarity(fingerprint, cohort_fingerprints)))

    pairs["max_tanimoto_to_chembl37"] = pairs["canonical_smiles"].map(maximum_similarity)
    stage_counts["similarity_overlap_excluded"] = int(
        pairs["max_tanimoto_to_chembl37"].ge(args.similarity_cutoff).sum()
    )
    pairs = pairs[pairs["max_tanimoto_to_chembl37"] < args.similarity_cutoff].copy()
    pairs["task"] = pairs[TARGET_COLUMN].map(TARGETS)
    pairs = pairs.sort_values(["task", "inchikey"]).reset_index(drop=True)
    stage_counts["strict_external_pairs"] = int(len(pairs))

    class_counts = counts_by_target_label(pairs)
    eligible = {
        task: counts["active"] >= args.minimum_class_count
        and counts["inactive"] >= args.minimum_class_count
        for task, counts in class_counts.items()
    }
    decision = (
        "eligible_for_three_target_confirmatory_external_validation"
        if all(eligible.values())
        else "insufficient_for_three_target_confirmatory_external_validation"
    )
    candidates_path = args.out / "candidates.parquet"
    pairs.drop(columns=["label_min", "label_max"]).to_parquet(candidates_path, index=False)
    manifest = {
        "kind": "bindingdb_external_validation_eligibility_audit",
        "created_at": datetime.now(UTC).isoformat(),
        "decision": decision,
        "reason": (
            "Every target must have the prespecified minimum active and inactive count after "
            "document, exact-molecule, and 0.70 chemical-similarity exclusion."
        ),
        "source": {
            "name": "BindingDB article-curated subset",
            "release": "2026-10",
            "url": SOURCE_URL,
            "license": "CC BY 4.0",
            "archive_md5": source_md5,
            "archive_sha256": source_sha256,
        },
        "selection": {
            "targets": TARGETS,
            "organism": "Homo sapiens",
            "single_protein_chain": True,
            "endpoints": ["Ki", "IC50"],
            "relations": ["="],
            "active_at_or_above_pchembl": 6.0,
            "inactive_at_or_below_pchembl": 5.0,
            "document_disjoint_from_chembl37": True,
            "exact_molecule_disjoint_from_chembl37": True,
            "maximum_tanimoto_to_chembl37_exclusive": args.similarity_cutoff,
            "minimum_active_and_inactive_per_target": args.minimum_class_count,
        },
        "stage_counts": stage_counts,
        "class_counts": class_counts,
        "target_inferential_eligibility": eligible,
        "all_targets_inferentially_eligible": all(eligible.values()),
        "candidate_rows_sha256": file_hash(candidates_path),
        "chembl_activities_sha256": file_hash(args.chembl_activities),
        "chembl_model_table_sha256": file_hash(args.chembl_model_table),
        "rdkit": rdBase.rdkitVersion,
    }
    (args.out / "audit.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

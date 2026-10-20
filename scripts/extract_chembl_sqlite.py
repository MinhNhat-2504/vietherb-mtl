#!/usr/bin/env python3
"""Extract the confirmatory activity cohort from a pinned ChEMBL SQLite DB."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yaml


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.out.exists() and not args.overwrite:
        raise FileExistsError(f"{args.out} exists; pass --overwrite explicitly")

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    target_ids = [item["id"] for item in config["targets"]]
    activity = config["retrieval"]
    standard_types = list(activity["standard_types"])
    assay_types = list(activity["assay_types"])
    placeholders_targets = ",".join("?" for _ in target_ids)
    placeholders_types = ",".join("?" for _ in standard_types)
    placeholders_assay_types = ",".join("?" for _ in assay_types)
    query = f"""
        SELECT td.chembl_id AS target_chembl_id,
               td.pref_name AS target_name,
               md.chembl_id AS molecule_chembl_id,
               cs.canonical_smiles,
               cs.standard_inchi_key,
               a.standard_type,
               a.standard_relation,
               a.standard_value,
               a.standard_units,
               a.pchembl_value,
               ass.chembl_id AS assay_chembl_id,
               ass.confidence_score,
               d.chembl_id AS document_chembl_id,
               d.year AS document_year,
               a.data_validity_comment,
               a.potential_duplicate
          FROM activities a
          JOIN assays ass ON a.assay_id = ass.assay_id
          JOIN target_dictionary td ON ass.tid = td.tid
          JOIN molecule_dictionary md ON a.molregno = md.molregno
          JOIN compound_structures cs ON md.molregno = cs.molregno
          LEFT JOIN docs d ON ass.doc_id = d.doc_id
         WHERE td.chembl_id IN ({placeholders_targets})
           AND td.target_type = ?
           AND td.organism = ?
           AND a.standard_type IN ({placeholders_types})
           AND ass.assay_type IN ({placeholders_assay_types})
           AND a.standard_units = ?
           AND a.pchembl_value IS NOT NULL
           AND ass.confidence_score >= ?
           AND (a.data_validity_comment IS NULL OR a.data_validity_comment = '')
           AND COALESCE(a.potential_duplicate, 0) = 0
    """
    parameters = [
        *target_ids,
        activity["target_type"],
        "Homo sapiens",
        *standard_types,
        *assay_types,
        activity["standard_units"],
        activity["assay_confidence_min"],
    ]
    with sqlite3.connect(f"file:{args.db.resolve()}?mode=ro", uri=True) as connection:
        frame = pd.read_sql_query(query, connection, params=parameters)
        try:
            version_rows = connection.execute("SELECT * FROM version").fetchall()
        except sqlite3.DatabaseError:
            version_rows = []
    args.out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(args.out, index=False)
    manifest = {
        "kind": "pinned_chembl_sqlite_extract",
        "requested_release": config["chembl_release"],
        "database": str(args.db),
        "database_sha256": file_hash(args.db),
        "database_version_rows": version_rows,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "rows": len(frame),
        "targets": frame["target_chembl_id"].value_counts().to_dict(),
        "output": args.out.name,
        "output_sha256": file_hash(args.out),
        "query": "Whitespace-normalized SQL is stored in this script version.",
    }
    args.out.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"rows": len(frame), "targets": manifest["targets"]}, indent=2))


if __name__ == "__main__":
    main()

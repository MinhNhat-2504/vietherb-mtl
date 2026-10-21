#!/usr/bin/env python3
"""Extract an auditable confirmatory cohort from a pinned ChEMBL SQLite release.

The CLI accepts either an already unpacked database or the official ``.tar.gz``
archive. Archive mode verifies the configured SHA-256, extracts into a temporary
directory beside the output, runs the query, and removes the ~30 GB database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import tarfile
import tempfile
from collections.abc import Callable
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

CHUNK_SIZE = 1024 * 1024
MIN_FREE_BYTES = 32 * 1024**3


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_release(value: object) -> str:
    return str(value).strip().upper().replace("CHEMBL_", "").replace("CHEMBL", "")


def database_release(connection: sqlite3.Connection) -> tuple[str, list[list[Any]]]:
    columns = [row[1] for row in connection.execute("PRAGMA table_info(version)")]
    rows = [list(row) for row in connection.execute("SELECT * FROM version").fetchall()]
    if not rows or "name" not in columns:
        raise RuntimeError("ChEMBL database has no readable release name in table 'version'")
    name_index = columns.index("name")
    release_rows = [
        row for row in rows if re.fullmatch(r"ChEMBL_?\d+", str(row[name_index]), re.IGNORECASE)
    ]
    if len(release_rows) != 1:
        names = [str(row[name_index]) for row in rows]
        raise RuntimeError(f"expected one ChEMBL release row, found names: {names}")
    return str(release_rows[0][name_index]), rows


def validate_targets(
    connection: sqlite3.Connection, target_config: list[dict[str, Any]], target_type: str
) -> dict[str, dict[str, Any]]:
    target_ids = [item["id"] for item in target_config]
    placeholders = ",".join("?" for _ in target_ids)
    query = f"""
        SELECT td.chembl_id,
               td.pref_name,
               td.target_type,
               td.organism,
               COUNT(tc.component_id) AS component_count,
               MAX(cs.accession) AS target_uniprot,
               MAX(cs.sequence) AS target_sequence
          FROM target_dictionary td
          LEFT JOIN target_components tc ON tc.tid = td.tid
          LEFT JOIN component_sequences cs ON cs.component_id = tc.component_id
         WHERE td.chembl_id IN ({placeholders})
         GROUP BY td.tid, td.chembl_id, td.pref_name, td.target_type, td.organism
    """
    records = pd.read_sql_query(query, connection, params=target_ids).to_dict("records")
    found = {str(record["chembl_id"]): record for record in records}
    errors: list[str] = []
    for expected in target_config:
        target_id = expected["id"]
        record = found.get(target_id)
        if record is None:
            errors.append(f"{target_id}: missing from database")
            continue
        if record["target_type"] != target_type:
            errors.append(f"{target_id}: target_type={record['target_type']!r}")
        if record["organism"] != expected["organism"]:
            errors.append(f"{target_id}: organism={record['organism']!r}")
        if int(record["component_count"]) != 1:
            errors.append(f"{target_id}: component_count={record['component_count']}")
        if not record["target_uniprot"] or not record["target_sequence"]:
            errors.append(f"{target_id}: missing UniProt accession or sequence")
    unexpected = sorted(set(found) - set(target_ids))
    if unexpected:
        errors.append(f"unexpected targets returned: {unexpected}")
    if errors:
        raise RuntimeError("target assertions failed: " + "; ".join(errors))
    return found


def load_candidate_activities(
    connection: sqlite3.Connection, target_ids: list[str]
) -> pd.DataFrame:
    """Load all records for the three targets before applying cohort filters."""
    placeholders = ",".join("?" for _ in target_ids)
    query = f"""
        SELECT a.activity_id,
               td.chembl_id AS target_chembl_id,
               td.pref_name AS target_name,
               td.organism AS target_organism,
               seq.accession AS target_uniprot,
               seq.sequence AS target_sequence,
               md.chembl_id AS molecule_chembl_id,
               md.natural_product,
               cs.canonical_smiles,
               cs.standard_inchi,
               cs.standard_inchi_key,
               a.standard_type,
               a.standard_relation,
               a.standard_value,
               a.standard_units,
               a.pchembl_value,
               a.activity_comment,
               a.data_validity_comment,
               a.potential_duplicate,
               ass.assay_id,
               ass.chembl_id AS assay_chembl_id,
               ass.assay_type,
               ass.confidence_score,
               ass.description AS assay_description,
               d.chembl_id AS document_chembl_id,
               d.year AS document_year,
               d.doi,
               d.pubmed_id
          FROM activities a
          JOIN assays ass ON ass.assay_id = a.assay_id
          JOIN target_dictionary td ON td.tid = ass.tid
          JOIN target_components tc ON tc.tid = td.tid
          JOIN component_sequences seq ON seq.component_id = tc.component_id
          JOIN molecule_dictionary md ON md.molregno = a.molregno
          LEFT JOIN compound_structures cs ON cs.molregno = md.molregno
          LEFT JOIN docs d ON d.doc_id = ass.doc_id
         WHERE td.chembl_id IN ({placeholders})
         ORDER BY td.chembl_id, md.chembl_id, a.activity_id
    """
    return pd.read_sql_query(query, connection, params=target_ids)


def apply_filters(
    frame: pd.DataFrame, retrieval: dict[str, Any]
) -> tuple[pd.DataFrame, list[dict[str, int | str]]]:
    """Apply prespecified filters sequentially and return an exclusion flow."""
    flow: list[dict[str, int | str]] = []

    def keep(name: str, predicate: Callable[[pd.DataFrame], pd.Series]) -> None:
        nonlocal frame
        before = len(frame)
        mask = predicate(frame).fillna(False)
        frame = frame.loc[mask].copy()
        flow.append(
            {"step": name, "before": before, "after": len(frame), "excluded": before - len(frame)}
        )

    keep("standard_type", lambda x: x["standard_type"].isin(retrieval["standard_types"]))
    keep("assay_type", lambda x: x["assay_type"].isin(retrieval["assay_types"]))
    keep("standard_units", lambda x: x["standard_units"].eq(retrieval["standard_units"]))
    keep(
        "assay_confidence",
        lambda x: pd.to_numeric(x["confidence_score"], errors="coerce").ge(
            retrieval["assay_confidence_min"]
        ),
    )
    keep(
        "valid_positive_standard_value",
        lambda x: pd.to_numeric(x["standard_value"], errors="coerce").gt(0),
    )
    keep(
        "valid_pchembl",
        lambda x: pd.to_numeric(x["pchembl_value"], errors="coerce").notna(),
    )
    keep(
        "allowed_relation",
        lambda x: x["standard_relation"].isin(retrieval["allowed_relations"]),
    )
    keep(
        "no_validity_warning",
        lambda x: x["data_validity_comment"].isna() | x["data_validity_comment"].eq(""),
    )
    keep(
        "not_potential_duplicate",
        lambda x: pd.to_numeric(x["potential_duplicate"], errors="coerce").fillna(0).eq(0),
    )
    keep(
        "resolved_structure",
        lambda x: x["canonical_smiles"].notna()
        & x["standard_inchi_key"].notna()
        & x["canonical_smiles"].ne(""),
    )
    return frame.reset_index(drop=True), flow


def extract_database(
    db_path: Path, config: dict[str, Any]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    connection = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    with closing(connection):
        connection.execute("PRAGMA query_only = ON")
        release, version_rows = database_release(connection)
        requested = config["chembl_release"]
        if normalized_release(release) != normalized_release(requested):
            raise RuntimeError(
                f"database reports {release!r}, but config requests ChEMBL {requested}"
            )
        targets = validate_targets(
            connection, config["targets"], config["retrieval"]["target_type"]
        )
        candidates = load_candidate_activities(connection, list(targets))
    filtered, flow = apply_filters(candidates, config["retrieval"])
    if filtered.empty:
        raise RuntimeError("no ChEMBL activities survived the prespecified filters")
    audit = {
        "database_release": release,
        "database_version_rows": version_rows,
        "validated_targets": targets,
        "candidate_rows": len(candidates),
        "exclusion_flow": flow,
    }
    return filtered, audit


def verify_archive(path: Path, config: dict[str, Any]) -> str:
    expected = str(config["source"]["archive_sha256"]).lower()
    observed = file_hash(path)
    if observed != expected:
        raise RuntimeError(f"archive SHA-256 mismatch: expected {expected}, observed {observed}")
    return observed


def unpack_database(archive_path: Path, destination: Path) -> Path:
    free = shutil.disk_usage(destination.parent).free
    if free < MIN_FREE_BYTES:
        raise RuntimeError(
            f"only {free / 1024**3:.1f} GiB free; temporary ChEMBL extraction requires "
            f"at least {MIN_FREE_BYTES / 1024**3:.0f} GiB"
        )
    with tarfile.open(archive_path, "r:gz") as archive:
        archive.extractall(destination, filter="data")
    candidates = sorted(destination.rglob("*.db"))
    if not candidates:
        raise RuntimeError("official archive contained no SQLite .db file")
    return max(candidates, key=lambda item: item.stat().st_size)


def write_outputs(
    frame: pd.DataFrame,
    audit: dict[str, Any],
    args: argparse.Namespace,
    config: dict[str, Any],
    db_path: Path,
    archive_sha256: str | None,
) -> None:
    args.out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(args.out, index=False)
    manifest = {
        "kind": "pinned_chembl_sqlite_extract",
        "requested_release": config["chembl_release"],
        "retrieved_at": datetime.now(UTC).isoformat(),
        "source": config.get("source", {}),
        "archive": str(args.tarball or args.archive_provenance)
        if (args.tarball or args.archive_provenance)
        else None,
        "archive_sha256": archive_sha256,
        "database_filename": db_path.name,
        "database_sha256": file_hash(db_path),
        **audit,
        "rows": len(frame),
        "targets": {
            str(key): int(value)
            for key, value in frame["target_chembl_id"].value_counts().sort_index().items()
        },
        "activity_types": {
            str(key): int(value)
            for key, value in frame["standard_type"].value_counts().sort_index().items()
        },
        "relations": {
            str(key): int(value)
            for key, value in frame["standard_relation"].value_counts().sort_index().items()
        },
        "output": args.out.name,
        "output_sha256": file_hash(args.out),
    }
    args.out.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8"
    )
    print(json.dumps({"rows": len(frame), "targets": manifest["targets"]}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--db", type=Path)
    source.add_argument("--tarball", type=Path)
    parser.add_argument(
        "--archive-provenance",
        type=Path,
        help="with --db, verify and record the official archive that produced the database",
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.out.exists() and not args.overwrite:
        raise FileExistsError(f"{args.out} exists; pass --overwrite explicitly")
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))

    archive_sha256: str | None = None
    if args.tarball:
        archive_sha256 = verify_archive(args.tarball, config)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="chembl37-", dir=args.out.parent) as temporary:
            db_path = unpack_database(args.tarball, Path(temporary))
            frame, audit = extract_database(db_path, config)
            write_outputs(frame, audit, args, config, db_path, archive_sha256)
    else:
        if not args.db.is_file():
            raise FileNotFoundError(args.db)
        if args.archive_provenance:
            archive_sha256 = verify_archive(args.archive_provenance, config)
        frame, audit = extract_database(args.db, config)
        write_outputs(frame, audit, args, config, args.db, archive_sha256)


if __name__ == "__main__":
    main()

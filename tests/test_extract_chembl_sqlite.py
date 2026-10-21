from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def extractor():
    return load_script("extract_chembl_sqlite", "extract_chembl_sqlite.py")


@pytest.fixture()
def mock_database(tmp_path: Path) -> Path:
    path = tmp_path / "chembl_37.db"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE version (name TEXT, creation_date TEXT);
        CREATE TABLE target_dictionary (
            tid INTEGER PRIMARY KEY, chembl_id TEXT, pref_name TEXT,
            target_type TEXT, organism TEXT
        );
        CREATE TABLE target_components (tid INTEGER, component_id INTEGER);
        CREATE TABLE component_sequences (
            component_id INTEGER PRIMARY KEY, accession TEXT, sequence TEXT
        );
        CREATE TABLE molecule_dictionary (
            molregno INTEGER PRIMARY KEY, chembl_id TEXT, natural_product INTEGER
        );
        CREATE TABLE compound_structures (
            molregno INTEGER PRIMARY KEY, canonical_smiles TEXT,
            standard_inchi TEXT, standard_inchi_key TEXT
        );
        CREATE TABLE docs (
            doc_id INTEGER PRIMARY KEY, chembl_id TEXT, year INTEGER,
            doi TEXT, pubmed_id INTEGER
        );
        CREATE TABLE assays (
            assay_id INTEGER PRIMARY KEY, chembl_id TEXT, tid INTEGER, doc_id INTEGER,
            assay_type TEXT, confidence_score INTEGER, description TEXT
        );
        CREATE TABLE activities (
            activity_id INTEGER PRIMARY KEY, assay_id INTEGER, molregno INTEGER,
            standard_type TEXT, standard_relation TEXT, standard_value REAL,
            standard_units TEXT, pchembl_value REAL, activity_comment TEXT,
            data_validity_comment TEXT, potential_duplicate INTEGER
        );
        """
    )
    connection.execute("INSERT INTO version VALUES ('ChEMBL_37', '2026-05-01')")
    connection.execute(
        "INSERT INTO target_dictionary VALUES (1, 'CHEMBL284', 'DPP4', "
        "'SINGLE PROTEIN', 'Homo sapiens')"
    )
    connection.execute("INSERT INTO target_components VALUES (1, 10)")
    connection.execute("INSERT INTO component_sequences VALUES (10, 'P27487', 'MAA')")
    connection.execute("INSERT INTO docs VALUES (1, 'CHEMBL_DOC_1', 2025, '10.1/x', 7)")
    connection.execute(
        "INSERT INTO assays VALUES (1, 'CHEMBL_ASSAY_1', 1, 1, 'B', 9, 'binding')"
    )
    for index in range(1, 6):
        connection.execute(
            "INSERT INTO molecule_dictionary VALUES (?, ?, ?)",
            (index, f"CHEMBL{index}", index % 2),
        )
        connection.execute(
            "INSERT INTO compound_structures VALUES (?, 'CCO', 'InChI=1S/x', ?)",
            (index, f"KEY{index}"),
        )
    rows = [
        (1, 1, 1, "IC50", "=", 100.0, "nM", 7.0, None, None, 0),
        (2, 1, 2, "Ki", "=", 10000.0, "nM", 5.0, None, None, 0),
        (3, 1, 3, "IC50", "=", 1000.0, "nM", 5.5, None, None, 0),
        (4, 1, 4, "IC50", ">", 10000.0, "nM", 5.0, None, None, 0),
        (5, 1, 5, "IC50", "=", 100.0, "nM", 7.0, None, None, 1),
    ]
    connection.executemany(
        "INSERT INTO activities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows
    )
    connection.commit()
    connection.close()
    return path


def config() -> dict:
    return {
        "chembl_release": 37,
        "retrieval": {
            "standard_types": ["IC50", "Ki"],
            "standard_units": "nM",
            "target_type": "SINGLE PROTEIN",
            "assay_confidence_min": 8,
            "assay_types": ["B"],
            "allowed_relations": ["="],
        },
        "targets": [
            {
                "id": "CHEMBL284",
                "symbol": "DPP4",
                "organism": "Homo sapiens",
            }
        ],
    }


def test_extractor_asserts_release_target_and_filter_flow(extractor, mock_database):
    frame, audit = extractor.extract_database(mock_database, config())
    assert audit["database_release"] == "ChEMBL_37"
    assert audit["candidate_rows"] == 5
    assert frame["activity_id"].tolist() == [1, 2, 3]
    assert audit["exclusion_flow"][-1]["after"] == 3
    assert set(frame["target_uniprot"]) == {"P27487"}


def test_release_reader_ignores_ontology_versions(extractor, mock_database):
    connection = sqlite3.connect(mock_database)
    connection.execute("INSERT INTO version VALUES ('UBERON 2024-03-22', NULL)")
    connection.commit()
    release, rows = extractor.database_release(connection)
    connection.close()
    assert release == "ChEMBL_37"
    assert len(rows) == 2


def test_extractor_rejects_release_mismatch(extractor, mock_database):
    bad = config()
    bad["chembl_release"] = 36
    with pytest.raises(RuntimeError, match="config requests"):
        extractor.extract_database(mock_database, bad)


def test_primary_label_policy_drops_gray_zone():
    builder = load_script("build_dataset_script", "build_dataset.py")
    frame = pd.DataFrame({"pchembl_value": [4.9, 5.0, 5.5, 6.0, 7.0]})
    labelled, gray = builder.label_activity_pairs(
        frame,
        {
            "active_threshold_pchembl": 6.0,
            "inactive_threshold_pchembl": 5.0,
            "exclude_gray_zone": True,
        },
    )
    assert gray == 1
    assert labelled["active"].tolist() == [0.0, 0.0, 1.0, 1.0]


def test_chemical_similarity_is_a_connected_component_constraint():
    builder = load_script("build_dataset_components", "build_dataset.py")
    molecules = pd.DataFrame(
        {
            "molecule_id": ["a", "b", "c"],
            "canonical_smiles": ["CCCCCC", "CCCCCCC", "c1ccccc1"],
            "murcko_scaffold": ["", "", "c1ccccc1"],
        }
    )
    components = builder.component_ids(
        molecules,
        None,
        similarity_threshold=0.5,
        fingerprint_radius=2,
        fingerprint_bits=256,
    )
    assert components["a"] == components["b"]
    assert components["a"] != components["c"]

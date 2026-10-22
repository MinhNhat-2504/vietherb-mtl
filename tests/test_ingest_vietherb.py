from __future__ import annotations

import json
from pathlib import Path

from scripts import ingest_vietherb


def test_minimal_authorized_export_contract(tmp_path: Path, monkeypatch) -> None:
    source = Path(__file__).parent / "fixtures" / "vietherb_minimal"
    output = tmp_path / "processed"
    monkeypatch.setattr(
        "sys.argv",
        [
            "ingest_vietherb.py",
            "--input",
            str(source),
            "--out",
            str(output),
        ],
    )
    ingest_vietherb.main()
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["kind"] == "authorized_vietherb_export"
    assert manifest["accepted_structures"] == 2
    assert (output / "species_metabolites.parquet").exists()

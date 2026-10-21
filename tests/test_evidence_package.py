from pathlib import Path

from vietherb_mtl.evidence import archived_run, sha256


def test_archived_run_resolves_flat_release_files(tmp_path: Path) -> None:
    files = archived_run(tmp_path, "chembl37_activity")

    assert files.metrics == tmp_path / "chembl37_activity_metrics.csv"
    assert files.predictions == tmp_path / "chembl37_activity_predictions.parquet"
    assert files.manifest == tmp_path / "chembl37_activity_run_manifest.json"


def test_evidence_text_hash_is_line_ending_independent(tmp_path: Path) -> None:
    lf_path = tmp_path / "lf.csv"
    crlf_path = tmp_path / "crlf.csv"
    lf_path.write_bytes(b"a,b\n1,2\n")
    crlf_path.write_bytes(b"a,b\r\n1,2\r\n")

    assert sha256(lf_path) == sha256(crlf_path)

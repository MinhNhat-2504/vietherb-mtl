from pathlib import Path

from vietherb_mtl.evidence import archived_run, sha256, verify_artifact_hashes


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


def test_artifact_verification_treats_png_as_an_exact_gate(tmp_path: Path) -> None:
    result = verify_artifact_hashes(
        {"figures/figure.png": "expected"},
        {"figures/figure.png": "different"},
        tmp_path,
        allow_pdf_renderer_variance=True,
    )

    assert result.mismatched == ("figures/figure.png",)
    assert not result.passed


def test_pdf_variance_requires_exact_png_companion_and_valid_pdf(tmp_path: Path) -> None:
    figures = tmp_path / "figures"
    figures.mkdir()
    (figures / "figure.pdf").write_bytes(b"%PDF-1.4\nbody\n%%EOF\n")
    expected = {"figures/figure.pdf": "reference-pdf", "figures/figure.png": "same"}
    actual = {"figures/figure.pdf": "other-pdf", "figures/figure.png": "same"}

    result = verify_artifact_hashes(
        expected,
        actual,
        tmp_path,
        allow_pdf_renderer_variance=True,
    )

    assert result.passed
    assert result.tolerated_pdf_variance == ("figures/figure.pdf",)
    assert result.exact_matches == 1


def test_pdf_variance_is_strict_by_default(tmp_path: Path) -> None:
    figures = tmp_path / "figures"
    figures.mkdir()
    (figures / "figure.pdf").write_bytes(b"%PDF-1.4\nbody\n%%EOF\n")
    expected = {"figures/figure.pdf": "reference-pdf", "figures/figure.png": "same"}
    actual = {"figures/figure.pdf": "other-pdf", "figures/figure.png": "same"}

    result = verify_artifact_hashes(expected, actual, tmp_path)

    assert result.mismatched == ("figures/figure.pdf",)
    assert not result.passed

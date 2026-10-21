import hashlib
from pathlib import Path

from scripts.generate_release_manifest import sha256


def test_text_hash_is_stable_across_line_endings(tmp_path: Path) -> None:
    lf_path = tmp_path / "lf.txt"
    crlf_path = tmp_path / "crlf.txt"
    lf_path.write_bytes(b"first\nsecond\n")
    crlf_path.write_bytes(b"first\r\nsecond\r\n")

    lf_digest, lf_mode = sha256(lf_path)
    crlf_digest, crlf_mode = sha256(crlf_path)

    assert lf_mode == crlf_mode == "utf8_lf"
    assert lf_digest == crlf_digest


def test_binary_hash_remains_byte_exact(tmp_path: Path) -> None:
    binary_path = tmp_path / "artifact.bin"
    binary_path.write_bytes(b"prefix\x00\r\npayload")

    digest, mode = sha256(binary_path)

    assert mode == "raw"
    assert digest == hashlib.sha256(binary_path.read_bytes()).hexdigest()

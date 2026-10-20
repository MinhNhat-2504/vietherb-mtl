import pytest

from vietherb_mtl.config import FingerprintConfig
from vietherb_mtl.features import FingerprintEncoder


def test_hashed_fingerprint_is_deterministic_and_fixed_width():
    encoder = FingerprintEncoder(FingerprintConfig(n_bits=64, backend="hashed"))
    first = encoder.encode("CC(=O)O")
    second = encoder.encode("CC(=O)O")
    assert first == second
    assert len(first) == 64
    assert set(first) <= {0, 1}
    assert sum(first) > 0


def test_invalid_input_is_rejected():
    encoder = FingerprintEncoder(FingerprintConfig(backend="hashed"))
    with pytest.raises(ValueError, match="non-empty"):
        encoder.encode("")

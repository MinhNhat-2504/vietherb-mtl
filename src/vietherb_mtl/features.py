"""Molecular feature encoders with graceful optional RDKit support."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

from .config import FingerprintConfig


class FingerprintEncoder:
    """Encode SMILES into fixed-size binary fingerprints.

    Returned values are plain ``list[int]`` objects to keep NumPy optional. Use
    ``numpy.asarray`` or ``torch.as_tensor`` at the training boundary.
    """

    def __init__(self, config: FingerprintConfig | None = None) -> None:
        self.config = config or FingerprintConfig()
        self._rdkit = self._load_rdkit()
        if self.config.backend == "rdkit" and self._rdkit is None:
            raise ImportError(
                "RDKit fingerprinting was requested but rdkit is not installed. "
                "Install rdkit or select backend='hashed'."
            )
        self.backend = (
            "rdkit"
            if self.config.backend == "rdkit"
            or (self.config.backend == "auto" and self._rdkit is not None)
            else "hashed"
        )

    @staticmethod
    def _load_rdkit():
        try:
            from rdkit import Chem
            from rdkit.Chem import rdFingerprintGenerator
        except ImportError:
            return None
        return Chem, rdFingerprintGenerator

    def encode(self, smiles: str) -> list[int]:
        if not isinstance(smiles, str) or not smiles.strip():
            raise ValueError("smiles must be a non-empty string")
        if self.backend == "rdkit":
            return self._encode_rdkit(smiles)
        return self._encode_hashed(smiles)

    def transform(self, smiles: Sequence[str]) -> list[list[int]]:
        return [self.encode(value) for value in smiles]

    def _encode_rdkit(self, smiles: str) -> list[int]:
        assert self._rdkit is not None
        Chem, rdFingerprintGenerator = self._rdkit
        molecule = Chem.MolFromSmiles(smiles)
        if molecule is None:
            raise ValueError(f"invalid SMILES: {smiles!r}")
        generator = rdFingerprintGenerator.GetMorganGenerator(
            radius=self.config.radius,
            fpSize=self.config.n_bits,
            includeChirality=self.config.use_chirality,
        )
        return [int(bit) for bit in generator.GetFingerprint(molecule)]

    def _encode_hashed(self, smiles: str) -> list[int]:
        vector = [0] * self.config.n_bits
        # Domain-separate n-gram lengths and avoid Python's randomized hash().
        for width in range(self.config.ngram_min, self.config.ngram_max + 1):
            if width > len(smiles):
                continue
            for start in range(len(smiles) - width + 1):
                token = f"{width}:{smiles[start : start + width]}".encode()
                digest = hashlib.blake2b(token, digest_size=8).digest()
                index = int.from_bytes(digest, "little") % self.config.n_bits
                vector[index] = 1
        return vector

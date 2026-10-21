"""Validated configuration objects used by the baseline implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class FingerprintConfig:
    """Configuration for molecular fingerprints.

    ``backend="auto"`` uses RDKit Morgan fingerprints when RDKit is installed,
    and otherwise falls back to a deterministic hashed character n-gram vector.
    The latter is intended for smoke tests and ablations, not as a chemistry-aware
    replacement for Morgan fingerprints.
    """

    n_bits: int = 2048
    radius: int = 2
    use_chirality: bool = True
    backend: Literal["auto", "rdkit", "hashed"] = "auto"
    ngram_min: int = 1
    ngram_max: int = 4

    def __post_init__(self) -> None:
        if self.n_bits <= 0:
            raise ValueError("n_bits must be positive")
        if self.radius < 0:
            raise ValueError("radius cannot be negative")
        if self.ngram_min <= 0 or self.ngram_max < self.ngram_min:
            raise ValueError("expected 0 < ngram_min <= ngram_max")


@dataclass(frozen=True)
class ModelConfig:
    """Architecture and task definition for the multi-task MLP."""

    input_dim: int = 2048
    hidden_dims: tuple[int, ...] = (512, 256)
    primary_tasks: tuple[str, ...] = ("activity",)
    auxiliary_tasks: tuple[str, ...] = ("diabetes", "neuro", "inflammation")
    # Backward-compatible constructor alias. Prefer auxiliary_tasks for new code.
    auxiliary_task: str | None = None
    dropout: float = 0.2
    auxiliary_weight: float = 0.25

    def __post_init__(self) -> None:
        if self.input_dim <= 0:
            raise ValueError("input_dim must be positive")
        if not self.hidden_dims or any(size <= 0 for size in self.hidden_dims):
            raise ValueError("hidden_dims must contain positive dimensions")
        if not self.primary_tasks or any(not task for task in self.primary_tasks):
            raise ValueError("at least one non-empty primary task is required")
        if len(set(self.primary_tasks)) != len(self.primary_tasks):
            raise ValueError("primary task names must be unique")
        default_auxiliary_tasks = ("diabetes", "neuro", "inflammation")
        if self.auxiliary_task is not None:
            if not self.auxiliary_task:
                raise ValueError("auxiliary_task must be non-empty when supplied")
            if self.auxiliary_tasks != default_auxiliary_tasks:
                raise ValueError(
                    "use either auxiliary_tasks or the legacy auxiliary_task alias, not both"
                )
            object.__setattr__(self, "auxiliary_tasks", (self.auxiliary_task,))
        if any(not task for task in self.auxiliary_tasks):
            raise ValueError("auxiliary task names must be non-empty")
        if len(set(self.auxiliary_tasks)) != len(self.auxiliary_tasks):
            raise ValueError("auxiliary task names must be unique")
        overlap = set(self.primary_tasks) & set(self.auxiliary_tasks)
        if overlap:
            raise ValueError(f"primary and auxiliary task names overlap: {sorted(overlap)}")
        if not 0.0 <= self.dropout < 1.0:
            raise ValueError("dropout must be in [0, 1)")
        if self.auxiliary_weight < 0.0:
            raise ValueError("auxiliary_weight cannot be negative")


@dataclass(frozen=True)
class SplitConfig:
    """Ratios and seed for leakage-resistant grouped splits."""

    train_fraction: float = 0.8
    validation_fraction: float = 0.1
    test_fraction: float = 0.1
    seed: int = 42

    def __post_init__(self) -> None:
        fractions = (
            self.train_fraction,
            self.validation_fraction,
            self.test_fraction,
        )
        if any(value < 0 for value in fractions):
            raise ValueError("split fractions cannot be negative")
        if not abs(sum(fractions) - 1.0) < 1e-9:
            raise ValueError("split fractions must sum to 1")
        if self.train_fraction == 0:
            raise ValueError("train_fraction must be positive")

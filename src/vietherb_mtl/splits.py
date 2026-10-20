"""Deterministic grouped splits that prevent scaffold/species leakage."""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass
from typing import TypeVar

from .config import SplitConfig

Group = TypeVar("Group", bound=Hashable)


@dataclass(frozen=True)
class SplitIndices:
    train: tuple[int, ...]
    validation: tuple[int, ...]
    test: tuple[int, ...]

    def as_dict(self) -> dict[str, tuple[int, ...]]:
        return {
            "train": self.train,
            "validation": self.validation,
            "test": self.test,
        }


def group_split(groups: Sequence[Group], config: SplitConfig | None = None) -> SplitIndices:
    """Greedily balance complete groups across train/validation/test.

    No group can occur in more than one output partition. The seed resolves ties
    and makes the result reproducible. Exact row ratios are not always possible
    when groups are large; preserving group integrity takes precedence.
    """

    config = config or SplitConfig()
    if not groups:
        raise ValueError("cannot split an empty dataset")
    grouped: dict[Group, list[int]] = defaultdict(list)
    for index, group in enumerate(groups):
        if group is None:
            raise ValueError(f"missing group at row {index}")
        grouped[group].append(index)

    rng = random.Random(config.seed)
    buckets = list(grouped.values())
    rng.shuffle(buckets)
    buckets.sort(key=len, reverse=True)  # stable: seeded order breaks size ties

    names = ("train", "validation", "test")
    fractions = (
        config.train_fraction,
        config.validation_fraction,
        config.test_fraction,
    )
    desired = {
        name: fraction * len(groups) for name, fraction in zip(names, fractions, strict=True)
    }
    assigned: dict[str, list[int]] = {name: [] for name in names}

    for bucket in buckets:
        eligible = [name for name, fraction in zip(names, fractions, strict=True) if fraction > 0]
        destination = max(
            eligible,
            key=lambda name: (
                desired[name] - len(assigned[name]),
                -len(assigned[name]),
                -names.index(name),
            ),
        )
        assigned[destination].extend(bucket)

    return SplitIndices(
        train=tuple(sorted(assigned["train"])),
        validation=tuple(sorted(assigned["validation"])),
        test=tuple(sorted(assigned["test"])),
    )


def species_group_split(species: Sequence[str], config: SplitConfig | None = None) -> SplitIndices:
    """Split rows while keeping every normalized species in one partition."""

    normalized = []
    for index, value in enumerate(species):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"missing species at row {index}")
        normalized.append(" ".join(value.casefold().split()))
    return group_split(normalized, config)


def connected_component_split(
    *group_constraints: Sequence[Hashable],
    config: SplitConfig | None = None,
) -> SplitIndices:
    """Split rows by transitive connected components across group constraints.

    Rows are joined when they share a value in *any* constraint. Union-find then
    closes transitive bridges: for example, compounds with the same scaffold stay
    together, species groups stay together, and a scaffold shared across species
    also keeps both species' other compounds in the same partition.
    """

    if not group_constraints:
        raise ValueError("at least one group constraint is required")
    size = len(group_constraints[0])
    if size == 0:
        raise ValueError("cannot split an empty dataset")
    if any(len(groups) != size for groups in group_constraints):
        raise ValueError("all group constraints must have the same length")

    parent = list(range(size))
    rank = [0] * size

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root == right_root:
            return
        if rank[left_root] < rank[right_root]:
            left_root, right_root = right_root, left_root
        parent[right_root] = left_root
        if rank[left_root] == rank[right_root]:
            rank[left_root] += 1

    for constraint_index, groups in enumerate(group_constraints):
        first_seen: dict[Hashable, int] = {}
        for row_index, group in enumerate(groups):
            if group is None:
                raise ValueError(
                    f"missing group in constraint {constraint_index} at row {row_index}"
                )
            try:
                previous = first_seen.get(group)
            except TypeError as error:
                raise TypeError("group values must be hashable") from error
            if previous is None:
                first_seen[group] = row_index
            else:
                union(previous, row_index)

    components = [find(index) for index in range(size)]
    return group_split(components, config)


def bemis_murcko_scaffold(smiles: str, *, include_chirality: bool = False) -> str:
    """Return a canonical Bemis-Murcko scaffold (requires RDKit)."""

    try:
        from rdkit import Chem
        from rdkit.Chem.Scaffolds import MurckoScaffold
    except ImportError as error:
        raise ImportError(
            "scaffold splitting requires RDKit; install rdkit or pass a custom "
            "scaffold_fn to scaffold_group_split"
        ) from error
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        raise ValueError(f"invalid SMILES: {smiles!r}")
    scaffold = MurckoScaffold.GetScaffoldForMol(molecule)
    return Chem.MolToSmiles(scaffold, isomericSmiles=include_chirality)


def scaffold_group_split(
    smiles: Sequence[str],
    config: SplitConfig | None = None,
    *,
    scaffold_fn: Callable[[str], Hashable] | None = None,
    include_chirality: bool = False,
) -> SplitIndices:
    """Split compounds while keeping each molecular scaffold in one partition.

    ``scaffold_fn`` enables precomputed or alternative scaffolds without RDKit.
    Acyclic molecules share RDKit's empty Murcko scaffold by design, preventing
    overly optimistic leakage among this structurally weak group.
    """

    if scaffold_fn is None:

        def scaffold_fn(value: str) -> str:
            return bemis_murcko_scaffold(value, include_chirality=include_chirality)

    scaffolds = [scaffold_fn(value) for value in smiles]
    return group_split(scaffolds, config)


def scaffold_species_group_split(
    smiles: Sequence[str],
    species: Sequence[str],
    config: SplitConfig | None = None,
    *,
    scaffold_fn: Callable[[str], Hashable] | None = None,
    include_chirality: bool = False,
) -> SplitIndices:
    """Strict split enforcing scaffold and species isolation simultaneously."""

    if len(smiles) != len(species):
        raise ValueError("smiles and species must have the same length")
    if scaffold_fn is None:

        def scaffold_fn(value: str) -> str:
            return bemis_murcko_scaffold(value, include_chirality=include_chirality)

    scaffolds = [scaffold_fn(value) for value in smiles]
    normalized_species: list[str] = []
    for index, value in enumerate(species):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"missing species at row {index}")
        normalized_species.append(" ".join(value.casefold().split()))
    return connected_component_split(scaffolds, normalized_species, config=config)

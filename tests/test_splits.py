from vietherb_mtl.config import SplitConfig
from vietherb_mtl.splits import (
    connected_component_split,
    scaffold_group_split,
    scaffold_species_group_split,
    species_group_split,
)


def _partition_by_index(split):
    result = {}
    for name, indices in split.as_dict().items():
        for index in indices:
            result[index] = name
    return result


def test_species_split_is_reproducible_and_has_no_group_leakage():
    species = ["Plant A", "plant  a", "Plant B", "Plant C", "Plant B", "Plant D"]
    config = SplitConfig(0.5, 0.25, 0.25, seed=7)
    first = species_group_split(species, config)
    assert first == species_group_split(species, config)
    partition = _partition_by_index(first)
    assert partition[0] == partition[1]
    assert partition[2] == partition[4]
    assert set(partition) == set(range(len(species)))


def test_scaffold_split_accepts_custom_function_without_rdkit():
    smiles = ["ring:a", "ring:b", "chain:c", "chain:d", "other:e"]
    split = scaffold_group_split(
        smiles,
        SplitConfig(0.6, 0.2, 0.2, seed=1),
        scaffold_fn=lambda value: value.split(":")[0],
    )
    partition = _partition_by_index(split)
    assert partition[0] == partition[1]
    assert partition[2] == partition[3]


def test_connected_components_close_transitive_group_bridges():
    # Rows 0-1 share scaffold; rows 1-2 share species. All three must stay
    # together even though rows 0 and 2 share neither value directly.
    split = connected_component_split(
        ["s1", "s1", "s2", "s3", "s4"],
        ["plant-a", "plant-b", "plant-b", "plant-c", "plant-d"],
        config=SplitConfig(0.6, 0.2, 0.2, seed=5),
    )
    partition = _partition_by_index(split)
    assert partition[0] == partition[1] == partition[2]


def test_joint_scaffold_species_split_enforces_both_constraints_without_rdkit():
    smiles = ["s1:a", "s1:b", "s2:c", "s3:d", "s4:e"]
    species = ["Plant A", "Plant B", "plant b", "Plant C", "Plant D"]
    split = scaffold_species_group_split(
        smiles,
        species,
        SplitConfig(0.6, 0.2, 0.2, seed=5),
        scaffold_fn=lambda value: value.split(":")[0],
    )
    partition = _partition_by_index(split)
    assert partition[0] == partition[1] == partition[2]

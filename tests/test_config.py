import pytest

from vietherb_mtl.config import ModelConfig


def test_default_auxiliary_tasks_cover_ethnomedicine_buckets():
    assert ModelConfig().auxiliary_tasks == (
        "diabetes",
        "neuro",
        "inflammation",
    )


def test_legacy_auxiliary_alias_maps_to_single_task():
    config = ModelConfig(auxiliary_task="ethnomedical")
    assert config.auxiliary_tasks == ("ethnomedical",)


def test_primary_auxiliary_task_overlap_is_rejected():
    with pytest.raises(ValueError, match="overlap"):
        ModelConfig(primary_tasks=("diabetes",))

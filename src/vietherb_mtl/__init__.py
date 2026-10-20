"""Small, dependency-light building blocks for VietHerb-MTL experiments."""

from .config import FingerprintConfig, ModelConfig, SplitConfig
from .features import FingerprintEncoder
from .losses import masked_bce_with_logits, multitask_masked_bce, nnpu_loss
from .metrics import bedroc_score, ef1_score, enrichment_factor, pr_auc_score
from .mil import AttentionMILAggregator, bag_masked_bce_with_logits, bag_nnpu_loss
from .model import MultiTaskMLP
from .splits import (
    SplitIndices,
    bemis_murcko_scaffold,
    connected_component_split,
    group_split,
    scaffold_group_split,
    scaffold_species_group_split,
    species_group_split,
)

__all__ = [
    "FingerprintConfig",
    "ModelConfig",
    "SplitConfig",
    "FingerprintEncoder",
    "MultiTaskMLP",
    "masked_bce_with_logits",
    "multitask_masked_bce",
    "nnpu_loss",
    "AttentionMILAggregator",
    "bag_masked_bce_with_logits",
    "bag_nnpu_loss",
    "SplitIndices",
    "bemis_murcko_scaffold",
    "connected_component_split",
    "group_split",
    "scaffold_group_split",
    "scaffold_species_group_split",
    "species_group_split",
    "pr_auc_score",
    "bedroc_score",
    "enrichment_factor",
    "ef1_score",
]

__version__ = "0.1.0"

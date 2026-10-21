"""Small, dependency-light building blocks for VietHerb-MTL experiments."""

from .config import FingerprintConfig, ModelConfig, SplitConfig
from .features import FingerprintEncoder
from .losses import masked_bce_with_logits, multitask_masked_bce, nnpu_loss
from .metrics import (
    bedroc_score,
    benjamini_hochberg,
    ef1_score,
    ef5_score,
    enrichment_factor,
    expected_calibration_error,
    mean_absolute_error,
    pr_auc_score,
    precision_recall_at_fraction,
    reliability_bins,
    root_mean_squared_error,
    spearman_correlation,
)
from .mil import AttentionMILAggregator, bag_masked_bce_with_logits, bag_nnpu_loss
from .model import MultiTaskMLP
from .selection import select_validation_configuration
from .splits import (
    SplitIndices,
    bemis_murcko_scaffold,
    connected_component_split,
    group_split,
    scaffold_group_split,
    scaffold_species_group_split,
    species_group_split,
    temporal_group_split,
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
    "temporal_group_split",
    "pr_auc_score",
    "bedroc_score",
    "enrichment_factor",
    "ef1_score",
    "ef5_score",
    "precision_recall_at_fraction",
    "expected_calibration_error",
    "reliability_bins",
    "mean_absolute_error",
    "root_mean_squared_error",
    "spearman_correlation",
    "benjamini_hochberg",
    "select_validation_configuration",
]

__version__ = "0.2.0"

# ChEMBL 37 activity-only baseline results

> **Confirmatory activity branch only.** These results use the frozen ChEMBL 37 cohort, but contain no authorized VietHerb bags and do not test the central MIL claim.

Generated at 2026-10-20T20:50:27.014107+00:00 from five fixed seeds.

## Macro PR-AUC

| Model | Mean | SD |
|---|---:|---:|
| single_task_mlp | 0.9281 | 0.0035 |
| shared_primary | 0.9203 | 0.0024 |

## Per-target PR-AUC

| Model | Target | Mean | SD |
|---|---|---:|---:|
| shared_primary | activity_ACHE | 0.8509 | 0.0104 |
| shared_primary | activity_DPP4 | 0.9889 | 0.0013 |
| shared_primary | activity_PTGS2 | 0.9212 | 0.0042 |
| single_task_mlp | activity_ACHE | 0.8781 | 0.0096 |
| single_task_mlp | activity_DPP4 | 0.9844 | 0.0035 |
| single_task_mlp | activity_PTGS2 | 0.9217 | 0.0030 |

## Paired shared_primary minus single_task_mlp

Observed macro PR-AUC difference: **-0.0077**. Hierarchical seed + chemical-component bootstrap 95% CI: **[-0.0141, -0.0021]** (1000 replicates).

The comparison evaluates the activity-only branch. It does not test the paper's ethnopharmacology/MIL hypothesis.

## Input hashes

- `outputs\chembl37_activity_baselines_v1\metrics.csv`: `59ad2bc7a0ee42d7c145f380885f749f8e55591f13c4dbfe2d914b6740be191d`
- `outputs\chembl37_activity_baselines_v1\predictions.parquet`: `d54d57ce6a6d82443c71d444939afc82144dd37ce7d45256435dd75d14f1d3f4`

# Exploratory baseline results

> **Not confirmatory.** These results use a live ChEMBL REST snapshot, not the frozen ChEMBL 37 SQLite release, and contain no authorized VietHerb bags.

Archived dataset, audit, and run provenance is available in
[`docs/manifests`](manifests/README.md).

Generated at 2026-10-20T19:14:09.027595+00:00 from five fixed seeds.

## Macro PR-AUC

| Model | Mean | SD |
|---|---:|---:|
| extra_trees | 0.8842 | 0.0010 |
| shared_primary | 0.8635 | 0.0019 |
| single_task_mlp | 0.8546 | 0.0045 |
| logistic_regression | 0.8358 | 0.0000 |

## Per-target PR-AUC

| Model | Target | Mean | SD |
|---|---|---:|---:|
| extra_trees | activity_ACHE | 0.8807 | 0.0016 |
| extra_trees | activity_DPP4 | 0.9627 | 0.0016 |
| extra_trees | activity_PTGS2 | 0.8092 | 0.0027 |
| logistic_regression | activity_ACHE | 0.8151 | 0.0000 |
| logistic_regression | activity_DPP4 | 0.9323 | 0.0000 |
| logistic_regression | activity_PTGS2 | 0.7600 | 0.0000 |
| shared_primary | activity_ACHE | 0.8490 | 0.0031 |
| shared_primary | activity_DPP4 | 0.9519 | 0.0019 |
| shared_primary | activity_PTGS2 | 0.7898 | 0.0046 |
| single_task_mlp | activity_ACHE | 0.8463 | 0.0049 |
| single_task_mlp | activity_DPP4 | 0.9417 | 0.0045 |
| single_task_mlp | activity_PTGS2 | 0.7758 | 0.0152 |

## Paired shared_primary minus single_task_mlp

Observed macro PR-AUC difference: **+0.0089**. Hierarchical seed + scaffold-component bootstrap 95% CI: **[+0.0034, +0.0154]** (1000 replicates).

The comparison is an engineering validation of the activity-only pipeline. It does not test the paper's ethnopharmacology/MIL hypothesis.

## Input hashes

- `outputs\chembl_live_exploratory_baselines\metrics.csv`: `a491028455d14177923aae987ccf082413b6005b9bb7929cd6da39211899605b`
- `outputs\chembl_live_classical\metrics.csv`: `2ee37e206b6af8e4e1c4401cfa94dbd20c49eaff43d833bcce0256759e8a8071`
- `outputs\chembl_live_exploratory_baselines\predictions.parquet`: `98957ffd3a5a68a2d7f253de9d6bfee0a13a2585f687773160cacf773a9e13b2`
- `outputs\chembl_live_classical\predictions.parquet`: `4624f05a07fbe711e2ccba3532df8ca9a5c6fdbb859e33a98265ec1ec4c4b163`

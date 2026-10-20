# VietHerb-MTL

Reproducible research code for **ethnopharmacology-informed multi-task learning
for multi-target screening of Vietnamese medicinal-plant metabolites**.

The central hypothesis is testable: a molecular encoder trained jointly on
measured target activity and **plant-level** traditional-use bags will rank
held-out natural products better than the same encoder trained on activity
alone. A gated-attention multiple-instance learner connects each plant bag to
its reported metabolites without pretending that every metabolite explains the
plant's use. The repository treats ethnomedical labels as noisy auxiliary
supervision—not as evidence of efficacy.

> **Project status:** the software pipeline is implemented and validated, and
> an activity-only exploratory ChEMBL snapshot has been analysed. No result for
> the central ethnopharmacology/MIL hypothesis is claimed until an authorized
> VietHerb export and the frozen confirmatory ChEMBL release are available.
> Generated demo data are only for software smoke tests. See the
> [current project status](docs/project_status.md) and
> [exploratory results](docs/exploratory_results.md).

## Study design

The first registered experiment uses three human targets with sufficient
ChEMBL depth:

| Target | ChEMBL ID | Disease context | Current API feasibility count* |
|---|---|---|---:|
| Dipeptidyl peptidase 4 | CHEMBL284 | type-2 diabetes | 6,390 |
| Acetylcholinesterase | CHEMBL220 | Alzheimer's disease | 9,701 |
| Prostaglandin G/H synthase 2 (COX-2) | CHEMBL230 | inflammation | 7,511 |

\*Counts were queried on 2026-10-20 for `IC50`/`Ki` measurements in nM and
are feasibility figures, not final curated sample counts.

The confirmatory comparison is:

1. single-task Morgan-fingerprint baseline;
2. shared encoder trained only on molecular-target activity;
3. naive propagation of plant labels to metabolites (falsification baseline);
4. shared encoder plus plant-bag multiple-instance supervision;
5. shuffled-bag-label control and natural-product importance weighting.

Primary evaluation uses scaffold-disjoint test compounds. VietHerb-derived
samples additionally enforce plant-species grouping. PR-AUC is the primary
metric; BEDROC (alpha 20), EF1%, ROC-AUC, and calibration are secondary.
Confidence intervals are compound-level stratified bootstrap intervals.

## Repository layout

```text
configs/                 Frozen data and experiment configurations
data/                    Schemas and annotation instructions (large data ignored)
docs/                    Protocol, source audit, and literature review
paper/                   English manuscript and bibliography
scripts/                 Acquisition, preparation, demo, and experiment entry points
src/vietherb_mtl/        Reusable model, split, metric, and training code
tests/                   Unit and leakage-invariant tests
```

## Environment

Use Python 3.11 or 3.12. The host Python 3.14 is intentionally unsupported by
the current scientific stack.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pytest
```

For an NVIDIA setup, install the PyTorch wheel matching the local CUDA driver
before installing this package. CPU execution is sufficient for tests and the
Morgan/MLP smoke experiment.

## Reproducible workflow

```powershell
# 1. Download target activities from the ChEMBL API (exploratory path only).
python scripts/fetch_chembl.py --config configs/targets_exploratory_snapshot.yaml `
  --out data/raw/chembl

# 2. Place an authorized VietHerb export under data/raw/vietherb, then validate it.
python scripts/ingest_vietherb.py --input data/raw/vietherb --out data/interim/vietherb

# For confirmatory results, use the version-pinned ChEMBL 37 SQLite release.
python scripts/extract_chembl_sqlite.py --db data/raw/chembl/37/chembl_37.db `
  --config configs/targets.yaml --out data/interim/chembl/37/activities.parquet

# 3. Build a frozen modelling table.
python scripts/build_dataset.py --config configs/dataset.yaml

# 4. Run the preregistered matrix.
python scripts/run_experiments.py --config configs/experiments/morgan_mlp.yaml
```

Until an authorized VietHerb export is available, a deterministic synthetic
dataset can exercise the whole software path:

```powershell
python scripts/make_demo_data.py --out data/processed/demo --seed 20261020
```

## Scientific safeguards

- Molecule structures are standardized before deduplication and splitting.
- Replicate activities are aggregated only after unit/relation checks; ambiguous
  contradictory measurements are retained as an explicit uncertainty flag.
- Split assignment is performed before fitting featurizers, thresholds, class
  weights, or domain weights.
- Scaffolds and VietHerb plant species must not cross split boundaries.
- Hyperparameters are selected on validation data only; the test set remains
  sealed until the analysis plan is frozen.
- LLM-assisted use-to-MeSH/Mondo mapping must be manually audited on a prespecified
  sample and reported with Cohen's kappa. Raw model suggestions are never
  treated as ground truth.
- Plant labels are optimized at bag level with attention MIL and PU risk. Label
  broadcasting is retained only as a named ablation.

See [the experiment protocol](docs/experiment_protocol.md) and
[data schema](data/README.md) before using real data.

## Citation and license

Code is released under the MIT License. Dataset licenses and access conditions
remain those of their original providers; do not redistribute VietHerb or other
source exports unless their terms explicitly permit it.


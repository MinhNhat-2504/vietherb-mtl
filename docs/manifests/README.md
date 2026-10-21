# Archived provenance and reproducibility artifacts

This directory contains two clearly separated artifact classes.

## Confirmatory ChEMBL 37 activity branch

The `chembl37_*` files are immutable copies of the frozen dataset audits,
dataset/run manifests, metrics, test predictions, temporal and continuous model
tables, and natural-product mapping used by the manuscript. Together with the
public ChEMBL 37 SQLite release and repository code, they reproduce every
reported numerical conclusion. The main evidence manifest in
`docs/evidence/manifest.json` binds the publication figures and tables to the
original run directories by SHA-256.

ChEMBL-derived data remain under the ChEMBL release terms (CC BY-SA 3.0); the
repository MIT licence applies to code, not to third-party data. No VietHerb
row is included in this directory.

## Exploratory live-API branch

Files named `chembl_live_*` are provenance copies from the exploratory ChEMBL
REST snapshot of 2026-10-20. They are not confirmatory evidence and explicitly
record `confirmatory_eligible: false`.

Generated neural checkpoints and the full upstream SQLite database are omitted
because they are large and regenerable. Synthetic smoke outputs are also
omitted because they are not scientific results.

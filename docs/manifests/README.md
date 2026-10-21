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

## External-validation eligibility audit

`bindingdb_external_audit.json` records the locked October 2026 BindingDB
article-subset audit. After document, exact-molecule, and 0.70 similarity
exclusion, DPP4 and PTGS2 did not meet the prespecified minimum of 30 active and
30 inactive pairs. The manifest therefore records an ineligible decision; it is
not a model-performance result. Raw BindingDB rows and the candidate Parquet are
omitted from this compact release and can be regenerated with the documented
provider snapshot and `scripts/audit_bindingdb_external.py`.

Generated neural checkpoints and the full upstream SQLite database are omitted
because they are large and regenerable. Synthetic smoke outputs are also
omitted because they are not scientific results.

All publication figures and tables can be regenerated directly from this flat
archive and checked against the frozen evidence hashes:

```powershell
python scripts/generate_evidence_package.py `
  --archive-dir docs/manifests `
  --out artifacts/reproduced_evidence `
  --verify-reference docs/evidence
```

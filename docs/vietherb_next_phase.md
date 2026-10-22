# VietHerb/MIL extension status

This is a prospective extension of the ChEMBL-only paper. No VietHerb row or
MIL result is part of the current manuscript.

## Gate 1: permission and export

The bilingual request in `docs/vietherb_permission_request.md` is approved by
both authors and ready to send to the VietHerb maintainers. Sending the email,
negotiating redistribution terms, and storing the reply are manual external
actions. Do not download or redistribute a live endpoint as a substitute for
written permission.

The minimum accepted export contains `species.csv`, `metabolites.csv`,
`species_metabolites.csv`, and `species_uses.csv`. After receipt, record the
provider version, date, licence, checksums, and permission identifier privately,
then run:

```powershell
python scripts/ingest_vietherb.py `
  --input data/raw/vietherb/authorized/<release> `
  --out data/interim/vietherb/authorized/<release>
```

## Gate 2: mapping and reviewer audit

Populate `data/annotations/therapeutic_use_mapping.csv` from a frozen ontology
and retain the original Vietnamese text. Two pharmacognosy/pharmacy reviewers
label the fixed, task/confidence-stratified 300-row sample independently. Run
`scripts/audit_therapeutic_mapping.py --require-complete`, adjudicate only after
agreement is computed, and freeze the mapping before opening any molecular test
results.

## Gate 3: botanical cold-start MIL

Once the export and mapping pass their gates, place the four validated tables
under `data/interim/vietherb/authorized/current`, build the dedicated dataset
with `configs/dataset_vietherb.yaml`, audit that no species bag crosses a split,
and run the
locked five-seed matrix from `configs/experiments/vietherb_mil_v1.yaml`:

```powershell
python scripts/build_dataset.py --config configs/dataset_vietherb.yaml --overwrite
python scripts/audit_dataset.py --dataset-dir data/processed/vietherb_v1
python scripts/run_experiments.py --config configs/experiments/vietherb_mil_v1.yaml
```

The confirmatory comparison is activity-only versus naive broadcast versus
attention MIL, with shuffled-label and prevalence-matched random controls. All
checkpoint selection is validation-only; report every seed, botanical
cold-start results, paired intervals, calibration, and attention-stability
diagnostics.

## Gate 4: independent/external validation

The existing BindingDB audit is underpowered for a three-target score and must
not be relabelled as external validation. A valid next route is either a new
source-disjoint, licence-compatible dataset that passes the same 30-active /
30-inactive gate for all targets, or a prospective biochemical assay.

For an assay, freeze candidates before seeing results using calibrated rank,
uncertainty, structural diversity, availability/purity, and interference-risk
filters. Pre-register target identity, positive/negative controls, replicate
count, concentration series, IC50/Ki fitting, counterscreens, blinding, and
failure criteria. A wet-lab collaborator and an approved protocol are required;
the repository cannot generate assay observations by itself.

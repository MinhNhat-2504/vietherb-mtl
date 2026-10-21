# Q1 submission execution roadmap

Updated: 2026-10-21 (Asia/Saigon)

This file is the ordered release gate for the empirical manuscript. A later
stage may be prepared while an external response is pending, but no stage may
be declared complete until its acceptance criteria pass.

## Gate 1 — VietHerb permission and export

Status: **ACTION REQUIRED FROM AUTHOR / MAINTAINER**

- [x] Verify the corresponding-author contact from the live site and paper.
- [x] Prepare bilingual permission/export request.
- [ ] Author confirms role, institution, and ORCID in the email.
- [ ] Send request to `ly.le@hcmiu.edu.vn`.
- [ ] Archive the response privately.
- [ ] Record snapshot identity, licence, attribution, redistribution scope, and
      permission identifier in a non-sensitive manifest.
- [ ] Receive the four required relational tables or permission to create a
      frozen, rate-limited snapshot.
- [ ] Confirm that a third party can access enough data to reproduce every
      conclusion intended for Journal of Cheminformatics.

Exit criterion: written terms and an export/access route support a reproducible
public benchmark. Internal-use-only permission does not pass this gate for the
current target journal.

## Gate 2 — Therapeutic-use normalization

Status: **BLOCKED BY GATE 1 AND DOMAIN REVIEWERS**

- Freeze MeSH/Mondo versions and synonym sources.
- Preserve all raw text and map the three target use families.
- Obtain two independent pharmacy/pharmacognosy reviews and adjudication.
- Report coverage, abstention, confusion modes, agreement, and Cohen's kappa.
- Freeze PU priors using training data only and prespecify sensitivity values.

Exit criterion: a versioned mapping table with reviewer fields complete and no
test-split information used during label construction.

## Gate 3 — Confirmatory ChEMBL 37 cohort

Status: **COMPLETE (2026-10-21)**

- [x] Locate the existing versioned ChEMBL 37 SQLite archive and verify the
  provider checksum without downloading a duplicate.
- [x] Verify release metadata and compute local SHA-256 checksums.
- [x] Complete relation, censoring, component/UniProt, organism, assay, duplicate,
  validity, and document-provenance assertions.
- [x] Freeze active/inactive/gray-zone policy before confirmatory model training.
- [x] Produce exclusion-flow and target-level audit tables.

Exit criterion: pinned extract and manifest pass all acceptance checks.

## Gate 4 — Split and evaluation hardening

Status: **IN PROGRESS**

- [x] Add the primary fingerprint-cluster chemical-OOD regime.
- [ ] Add a temporal holdout sensitivity regime.
- Retain strict scaffold/species connected components as a secondary regime.
- [x] Add nearest-neighbour Tanimoto and component-size diagnostics.
- Make auxiliary-weight and PU-prior selection validation-only; evaluate the
  sealed test set once per selected configuration.
- [x] Add EF5%, precision/recall at budget, and ECE metrics.
- [ ] Add reliability figures, continuous-potency sensitivity, per-target
  intervals, and multiplicity correction.

Exit criterion: unit-tested split/selection/metric code and a frozen analysis
plan exist before confirmatory training.

## Gate 5 — Confirmatory experiment matrix

Status: **ACTIVITY-ONLY BASELINE COMPLETE; MIL BLOCKED BY GATES 1–2 AND 4**

Run five fixed seeds for classical, single-task, shared activity-only,
naive-broadcast, MIL, shuffled-MIL, random-label, importance-weighted, and
Chemprop/D-MPNN baselines. Report both chemical-OOD and botanical cold-start;
add temporal and natural-product-subset analyses where sample sizes permit.

Completed subset: five-seed single-task and shared-activity MLPs on the frozen
chemical-OOD cohort, with predictions and run manifest archived. Classical,
Chemprop, temporal, natural-product, and all VietHerb-dependent arms remain.

Exit criterion: all real-data manifests are complete, synthetic flags are
false, leakage audits pass, and the primary paired comparison is computed from
sealed test predictions.

## Gate 6 — Evidence package and manuscript

Status: **BLOCKED BY GATE 5**

- Generate the data-flow, chemical-space, main-result, ablation, calibration,
  enrichment, cold-start, and interpretation figures from manifests.
- Expand Results and Discussion without duplicating supplementary audits.
- Add the required Scientific Contribution abstract subsection, keywords,
  affiliations, abbreviations, line numbering, and journal declarations.
- Archive code, processed data, predictions, splits, and environment with
  persistent releases/DOIs; prepare cover letter and optional graphical abstract.

Exit criterion: every claim maps to an archived artifact and the journal's
submission checklist passes.

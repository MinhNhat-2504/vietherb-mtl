# Project status

Updated: 2026-10-21 (Asia/Saigon)

## Completed

- ChEMBL 37 is checksum-locked and curated to 10,698 labelled pairs from
  10,686 unique molecules; 435 contradictory and 3,353 gray-zone pairs were
  excluded from the binary primary cohort.
- The 0.70 Morgan-Tanimoto chemical-OOD split contains
  7,480/1,603/1,603 molecules, zero identifier/InChIKey/scaffold/component
  overlap, and maximum test-to-train Tanimoto 0.698.
- Temporal and continuous sensitivity cohorts are frozen and audited.
- Validation-only model selection, reliability/calibration, continuous metrics,
  per-target hierarchical bootstrap, and Benjamini–Hochberg correction are
  implemented and unit tested.
- Five-seed chemical-OOD results are complete for logistic regression, Extra
  Trees, separate and shared MLPs, and official Chemprop 2.2.1 D-MPNN.
  Macro PR-AUC is 0.9334, 0.9425, 0.9281, 0.9203, and 0.8938, respectively.
- Shared-minus-separate MLP macro PR-AUC is -0.0077 (95% CI -0.0141 to
  -0.0021); the corrected deficit is localized to AChE.
- The temporal split reverses the neural result: shared MLP 0.9425 versus
  separate MLP 0.9247 macro PR-AUC. Continuous potency favors separate MLPs:
  MAE 0.8083 versus 0.8181.
- A natural-product-flag sensitivity was executed; only 79 flagged test
  molecules were present and no target met the 30-positive/30-negative
  inferential threshold.
- Six figures, six machine-readable tables, and a hash-bound evidence manifest
  have been generated. Main manuscript, supplement, cover letter, Zenodo
  metadata, and submission/release checklists are drafted.
- Forty-nine unit tests and a synthetic CUDA smoke workflow cover activity,
  broadcast, MIL, shuffled-MIL, selection, temporal split, metric, and leakage
  invariants, plus cross-platform release-manifest hashing. Synthetic metrics
  are never reported as scientific results.

## Scientific blockers

1. **VietHerb permission/export.** No explicit database redistribution licence
   was identified. A third-party reproducible access route is required before
   any empirical VietHerb/MIL conclusion can target Journal of Cheminformatics.
2. **Domain annotation.** Two pharmacy/pharmacognosy reviewers must freeze and
   adjudicate therapeutic-use mappings.
3. **True external validation.** MoleculeACE lacks CHEMBL220, CHEMBL230, and
   CHEMBL284 and is ChEMBL-derived. The completed temporal holdout is not an
   independent external biological dataset.

## Release blockers

- Both authors must confirm CRediT, funding, competing-interest, and approval
  statements.
- Final PDFs and repository tests must pass from the final working tree.
- The GitHub release must be archived in Zenodo and its version DOI inserted
  into the manuscript before submission.
- A clean-clone reproduction of the archived artifact bundle remains required.

See `docs/submission_roadmap.md` for the gate-by-gate checklist.

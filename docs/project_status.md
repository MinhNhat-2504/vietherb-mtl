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
- The October 2026 BindingDB article-curated subset was audited after ChEMBL 37
  document, exact-molecule, and 0.70 similarity exclusion. The remaining 233
  pairs met the 30-per-class gate only for AChE, not DPP4 or PTGS2; no
  underpowered external performance was calculated or claimed.
- Six figures, six machine-readable tables, and a hash-bound evidence manifest
  have been generated. Main manuscript, supplement, cover letter, Zenodo
  metadata, and submission/release checklists are drafted.
- A clean release bundle passed the complete unit-test suite, Ruff,
  release-hash verification, and exact regeneration of all 18 evidence
  artifacts. Runtime, OS, Python, and package versions are archived, and the
  same locked sequence passed the clean-checkout GitHub Actions Ubuntu runner
  for commit `4b2a80d` (run `39632670928`).
- The complete unit-test suite and a synthetic CUDA smoke workflow cover activity,
  broadcast, MIL, shuffled-MIL, selection, temporal split, metric, and leakage
  invariants, plus cross-platform release-manifest hashing. Synthetic metrics
  are never reported as scientific results.

## Scientific blockers

1. **VietHerb permission/export.** No explicit database redistribution licence
   was identified. A third-party reproducible access route is required before
   any empirical VietHerb/MIL conclusion can target Journal of Cheminformatics.
2. **Domain annotation.** Two pharmacy/pharmacognosy reviewers must freeze and
   adjudicate therapeutic-use mappings.

True external biological validation remains a valuable future extension, not a
completed result or a release blocker for the current ChEMBL-only paper. The
manuscript explicitly distinguishes temporal validation from external
validation.

## Release blockers

- Both authors must confirm CRediT, funding, competing-interest, and approval
  statements.
- GitHub release `v0.2.1` is archived in Zenodo as
  `10.5281/zenodo.23549035`; the version DOI is inserted into the manuscript
  and citation metadata before submission.
- The downloaded Zenodo ZIP passed checksum, release-manifest, test, Ruff, and
  evidence-replay verification. Its published record-level rights must still be
  changed from MIT-only to mixed MIT/CC BY-SA 3.0 terms.

See `docs/submission_roadmap.md` for the gate-by-gate checklist.

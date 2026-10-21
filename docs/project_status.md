# Project status

Updated: 2026-10-21 (Asia/Saigon)

## Completed

- Parsed the proposal PDF and narrowed Topic 2 to a defensible contribution.
- Initialized the empty GitHub repository locally with package metadata,
  licensing, data contracts, configurations, and reproducibility safeguards.
- Audited prior work through 2026-10-20. The broad novelty claim was rejected;
  the proposed method is now plant-bag/compound-instance MIL.
- Audited VietHerb, ChEMBL, LOTUS, COCONUT, and NPASS access, schemas, versions,
  overlap risks, and licence constraints.
- Implemented Morgan fingerprints, multi-target MLP heads, masked BCE, nnPU,
  gated-attention MIL, strict fingerprint/scaffold/species connected-component
  splits, PR-AUC, BEDROC20, EF1/EF5, fixed-budget metrics, ECE, extraction
  manifests, and audit gates.
- Passed 39 unit tests, Ruff, Python compilation, and a full synthetic GPU smoke
  experiment containing activity-only, naive-broadcast, MIL, and shuffled-MIL
  paths. Synthetic outputs are marked non-scientific.
- Downloaded an exploratory live ChEMBL snapshot (23,602 raw records), built a
  binding-assay cohort (14,051 curated pairs; 14,029 molecules), and verified
  zero molecule/InChIKey/scaffold/component overlap across splits.
- Ran five-seed fingerprint baselines. Exploratory macro PR-AUC:
  ExtraTrees 0.8842, shared MLP 0.8635, single-task MLP 0.8546, logistic
  regression 0.8358. Shared minus single-task MLP was +0.0089 with a
  hierarchical bootstrap 95% CI [0.0034, 0.0154]. These are not confirmatory and
  do not test the ethnopharmacology hypothesis.
- Verified the existing official ChEMBL 37 archive against provider SHA-256,
  extracted the three-target cohort, and recorded archive, SQLite, and output
  hashes. The frozen cohort has 16,941 eligible records, 10,698 labelled pairs,
  and 10,686 unique molecules after excluding 435 contradictory and 3,353
  gray-zone pairs.
- Built the locked 0.70 Morgan-Tanimoto chemical-OOD split (7,480/1,603/1,603).
  The audit found zero identifier/scaffold/component overlap; test-to-train
  maximum Tanimoto is 0.698.
- Ran the five-seed frozen activity-only neural comparison. Single-task MLPs
  reached macro PR-AUC 0.9281 versus 0.9203 for the shared MLP; paired delta
  -0.0077, chemical-component bootstrap 95% CI [-0.0141, -0.0021]. Shared
  learning improved BEDROC20 but worsened PR-AUC and calibration, a
  target/metric-dependent negative-transfer result.
- Completed and compiled an eight-page English protocol-plus-results
  manuscript. All reported values trace to archived real-data manifests; no
  synthetic performance or unsupported VietHerb/MIL result is presented.

## Release blockers

1. **VietHerb permission/export.** The public API is technically reachable, but
   no explicit data licence was found. Written permission is required before a
   row-level benchmark can be redistributed. The request template is in
   `docs/vietherb_permission_request.md`.
2. **Domain annotation.** Two pharmacy/pharmacognosy reviewers are needed to
   freeze and audit therapeutic-use mappings. LLM suggestions alone are not an
   acceptable label source.

## Next execution order

1. Obtain and record VietHerb permission; ingest the authorized four-table
   export and audit live-versus-paper count differences.
2. Freeze therapeutic-use mappings and class-prior sensitivity values.
3. Build botanical cold-start manifests, then run all five
   seeds for classical, activity-only, naive-broadcast, MIL, shuffled-label, and
   importance-weighted models.
4. Populate manuscript tables only from confirmatory manifests; then select
   candidates for orthogonal structure-based assessment or blinded assays.


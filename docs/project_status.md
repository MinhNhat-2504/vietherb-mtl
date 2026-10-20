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
  gated-attention MIL, strict scaffold/species connected-component splits,
  PR-AUC, BEDROC20, EF1%, ingestion/extraction scripts, and audit gates.
- Passed 32 unit tests, Ruff, Python compilation, and a full synthetic GPU smoke
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
- Drafted and compiled a seven-page English manuscript with explicit result
  locks and primary/secondary analysis language.

## Release blockers

1. **VietHerb permission/export.** The public API is technically reachable, but
   no explicit data licence was found. Written permission is required before a
   row-level benchmark can be redistributed. The request template is in
   `docs/vietherb_permission_request.md`.
2. **Domain annotation.** Two pharmacy/pharmacognosy reviewers are needed to
   freeze and audit therapeutic-use mappings. LLM suggestions alone are not an
   acceptable label source.
3. **Confirmatory ChEMBL snapshot.** Final results must use the versioned ChEMBL
   37 SQLite release rather than the live REST snapshot.

## Next execution order

1. Obtain and record VietHerb permission; ingest the authorized four-table
   export and audit live-versus-paper count differences.
2. Download/checksum ChEMBL 37 SQLite and re-run the frozen extraction.
3. Freeze therapeutic-use mappings and class-prior sensitivity values.
4. Build chemical-OOD and botanical cold-start manifests, then run all five
   seeds for classical, activity-only, naive-broadcast, MIL, shuffled-label, and
   importance-weighted models.
5. Populate manuscript tables only from confirmatory manifests; then select
   candidates for orthogonal structure-based assessment or blinded assays.


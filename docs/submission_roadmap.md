# Q1 submission execution roadmap

Updated: 2026-10-21 (Asia/Saigon)

This is the ordered release gate. “Complete” means that its acceptance checks
pass; a prepared draft is not equivalent to an external approval or DOI.

## 1 — VietHerb permission and export

Status: **ACTION REQUIRED FROM AUTHORS / MAINTAINER**

- [x] Verify the maintainer contact and prepare a bilingual request.
- [x] Add author order, affiliation, institutional emails, ORCIDs, and
  corresponding-author designation.
- [ ] Both authors confirm CRediT, funding, and competing-interest statements.
- [ ] Send the request to `ly.le@hcmiu.edu.vn` and archive the response privately.
- [ ] Receive an export/access route whose terms permit third-party
  reproducibility for every intended VietHerb conclusion.

Exit criterion: written terms and a frozen export/access route support a public,
reproducible benchmark. Internal-use-only permission does not pass this gate for
Journal of Cheminformatics.

## 2 — Therapeutic-use normalization

Status: **BLOCKED BY 1 AND DOMAIN REVIEWERS**

- Freeze MeSH/Mondo versions and preserve every source span.
- Obtain two independent pharmacy/pharmacognosy reviews and adjudication.
- Report coverage, abstention, confusion modes, agreement, and Cohen's kappa.
- Freeze training-only PU priors and sensitivity values.

Exit criterion: a versioned mapping table with complete reviewer fields and no
test information used in label construction.

## 3 — Freeze ChEMBL 37 and acceptance checks

Status: **COMPLETE (2026-10-21)**

- [x] Reuse and verify the local official ChEMBL 37 archive; no duplicate
  download was made.
- [x] Bind archive, SQLite, extract, cohort, and split artifacts by SHA-256.
- [x] Validate target/UniProt identity, organism, assay, relation, duplicate,
  validity, document provenance, contradiction, and gray-zone policies.
- [x] Freeze 10,698 labelled pairs, 10,686 molecules, and 7,480/1,603/1,603
  primary partitions.
- [x] Pass identity, InChIKey, scaffold, connected-component, and nearest-neighbour
  leakage audits; maximum test-to-train Tanimoto is 0.698.

## 4 — Split, metrics, and model selection

Status: **COMPLETE (2026-10-21)**

- [x] Primary 0.70 Tanimoto connected-component chemical-OOD split.
- [x] First-publication-year temporal split with future-label censoring.
- [x] Continuous-pChEMBL chemical-OOD sensitivity cohort.
- [x] EF1%, EF5%, fixed-budget precision/recall, AUROC, Brier, ECE, reliability
  bins, MAE, RMSE, Spearman, per-target bootstrap, and BH correction.
- [x] Validation-only configuration selection; the selector rejects test-metric
  columns and evaluates test only after selection/checkpoint restoration.
- [x] Unit tests cover the new invariants, archived evidence regeneration,
  and cross-platform release hashes.

## 5 — Confirmatory five-seed matrix

Status: **CHEMBL-ONLY ARMS COMPLETE; VIETHERB ARMS BLOCKED BY 1–2**

- [x] Five fixed seeds: 13, 37, 71, 101, 137.
- [x] Chemical-OOD logistic regression and Extra Trees.
- [x] Chemical-OOD separate and shared fingerprint MLPs.
- [x] Chemical-OOD official Chemprop 2.2.1 D-MPNN.
- [x] Temporal classical and neural baselines.
- [x] Continuous-pChEMBL separate/shared neural sensitivity.
- [x] Natural-product-flag subgroup; prespecified power threshold failed, so
  results are descriptive only.
- [ ] Real naive-broadcast, MIL, shuffled-MIL, random-label, importance-weighted,
  botanical cold-start, and attention-stability arms.

Principal chemical-OOD macro PR-AUC: Extra Trees 0.9425, logistic regression
0.9334, separate MLP 0.9281, shared MLP 0.9203, D-MPNN 0.8938. Every completed
run has `scientific_results=true`; synthetic smoke runs remain excluded.

## 6 — Chemprop and temporal/external validation

Status: **COMPLETE FOR CURRENT PAPER; PROSPECTIVE EXTERNAL EXTENSION OPEN**

- [x] Chemprop D-MPNN on the exact frozen split and five seeds.
- [x] Temporal holdout (train through 2017, validation 2018–2021, test
  2022–2025).
- [x] Assess MoleculeACE suitability. It lacks the three target IDs and is
  ChEMBL-derived, so it was not mislabelled as independent external validation.
- [x] Audit the October 2026 BindingDB article-curated subset after ChEMBL 37
  document, exact-molecule, and 0.70 chemical-similarity exclusion. Only AChE
  met the locked 30-active/30-inactive gate; DPP4 and PTGS2 did not.
- [x] Freeze the current-paper decision: report chemical-OOD and temporal
  validation, calculate no underpowered three-target external score, and make
  no independent-external-validation claim.
- [ ] Future extension: identify a sufficiently powered, licence-compatible,
  independently generated matched-target source or conduct prospective
  biochemical validation.

The manuscript calls the completed analysis “temporal validation,” not
“external validation.” The open extension is not a release blocker for the
current ChEMBL-only benchmark.

## 7 — Figures, tables, supplement, and manuscript

Status: **COMPLETE (2026-10-21)**

- [x] Six main figures as PDF and PNG.
- [x] Submission graphical abstract: 920 × 300 px, white background, 53.67 KB.
- [x] Six machine-readable evidence tables.
- [x] SHA-256 evidence manifest generated directly from run artifacts.
- [x] Main paper expanded with all real results, uncertainty, calibration,
  sensitivity analyses, limitations, and locked MIL boundary.
- [x] Additional file 1 drafted with cohort flow, selection policy, per-target
  results, environment, and provenance.
- [x] Journal-required Scientific Contribution, keywords, line/page numbering,
  and Declarations added.
- [x] Compile final PDFs and complete visual/warning inspection: main manuscript
  18 pages, Additional file 1 five pages, with no unresolved reference,
  citation, or overfull-box warnings.

## 8 — Zenodo, Springer submission package, and cover letter

Status: **PREPARED LOCALLY; DOI AND SUBMISSION REQUIRE AUTHOR ACCOUNT ACTION**

- [x] `CITATION.cff` and `.zenodo.json` metadata prepared.
- [x] Environment manifest, release procedure, submission checklist, and cover
  letter drafted.
- [x] Reproduce all 18 evidence artifacts and verify all release paths from
  a clean manifest-only bundle; archive runtime and environment metadata.
- [x] Manuscript uses accepted TeX/LaTeX source with double spacing and line/page
  numbering; vector figures and editable sources are retained.
- [ ] Both authors approve declarations and cover letter.
- [ ] Create `v0.1.0` GitHub release after final verification.
- [ ] Enable the repository in Zenodo, archive the release, verify it from a
  clean download, and insert the version DOI into manuscript/CITATION files.
- [ ] Upload through the journal account and confirm APC/funding arrangements.

Exit criterion: clean-clone reproduction succeeds, the DOI resolves to the exact
artifact set, all author declarations are approved, and the journal checklist
has no open mandatory item.

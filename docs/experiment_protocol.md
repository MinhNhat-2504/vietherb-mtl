# Confirmatory experiment protocol (v1)

**Frozen date:** 2026-10-20  
**Scope:** computational validation; docking and wet-lab validation are staged
extensions and are not prerequisites for the primary hypothesis test.

## Research question and hypotheses

Does weak supervision derived from documented Vietnamese traditional-medicine
uses improve out-of-scaffold ranking of natural products for molecular targets?

- **H1 (primary):** the multi-task model with audited ethnomedical auxiliary
  labels has higher macro PR-AUC than the architecture-matched activity-only
  model on the untouched scaffold/species-disjoint test set.
- **H2:** improvement is concentrated in natural products and low-label target
  regimes, consistent with a representation/regularization benefit.
- **H3:** training-domain importance weighting further improves natural-product
  test performance without materially reducing overall PR-AUC.
- **Negative control:** randomly permuting auxiliary labels within the training
  partition should remove the gain. A gain under permutation indicates capacity,
  optimization, or leakage effects rather than useful ethnomedical information.

Traditional-use labels are noisy historical observations. Even a positive H1
does not establish clinical efficacy or validate a traditional indication.

## Data cohorts

### Primary molecular activity

ChEMBL release 37 is the confirmatory source. Exploratory API downloads may be
used to debug the pipeline but must not produce the paper's final numbers.

Targets are DPP4 (`CHEMBL284`), AChE (`CHEMBL220`), and COX-2/PTGS2
(`CHEMBL230`). The primary cohort uses direct biochemical binding assays,
`IC50`/`Ki` observations in nM for human single-protein targets, assay
confidence at least 8, and a valid pChEMBL value. Functional assays are a
separate sensitivity cohort, not silently pooled. Exclude invalid/duplicate-
flagged measurements and records with ambiguous relations. The primary binary
analysis uses exact (`=`) observations only: pChEMBL >= 6 is active, pChEMBL <=
5 is inactive, and the open interval (5, 6) is excluded. Alternative cutoffs
and explicit censored/continuous models are sensitivity analyses.

Aggregate exact standardized structure/target replicates by median pChEMBL.
Flag a structure-target pair as contradictory when its valid replicates span at
least one log unit. The primary analysis excludes flagged pairs; the sensitivity
analysis retains their median label.

### Ethnomedical auxiliary labels

Obtain the VietHerb export from its maintainers or another explicitly authorized
source. Preserve raw species-metabolite and species-therapeutic-use edges. Map
raw use descriptions to a frozen ontology table. For v1, ontology terms are
collapsed into three target-aligned but non-identical families:

- diabetes/metabolic (`ethno_diabetes`);
- cognition/neurological (`ethno_neuro`);
- pain/inflammation (`ethno_inflammation`).

An observed use produces a positive weak label for metabolites reported in that
species. Unobserved uses are unlabelled, never negative. Auxiliary heads use a
non-negative positive-unlabelled (nnPU) objective with class priors estimated on
training data and varied in sensitivity analysis. If a molecule occurs in
several plants, retain all provenance before resolving duplicate weak labels.

Two pharmacognosy/pharmacy reviewers independently audit 300 mappings drawn
with a fixed random seed and stratified by ontology family and mapper confidence.
Report raw agreement, Cohen's kappa, and a bootstrap 95% confidence interval.
Freeze the decision table before opening the molecular-activity test set.

### Optional natural-product resources

COCONUT and LOTUS may add unlabeled structures for domain estimation or external
screening. They do not replace VietHerb use labels and are excluded from the
confirmatory test set. Every snapshot requires provider version, retrieval date,
license note, and SHA-256 checksums.

## Structure curation

Use RDKit with a recorded version. Parse structures; choose the largest organic
fragment; normalize supported functional groups; optionally neutralize; retain
stereochemistry; canonicalize tautomers; generate canonical isomeric SMILES and
standard InChIKey. Log each rejection and transformation. Deduplicate only after
standardization and retain source-to-canonical provenance.

## Leakage-resistant split

The primary split unit is a connected component of three constraints:

1. molecules with radius-2, 2048-bit chiral Morgan Tanimoto similarity at least
   0.70 are connected;
2. molecules with the same Bemis-Murcko scaffold are connected;
3. metabolites reported for the same VietHerb species are connected.

The transitive closure is essential: if molecule A shares a scaffold with B and
B shares a species with C, all three belong to one component. Assign entire
components to 70% train, 15% validation, and 15% test with seed 20261020 while
approximately preserving per-target labels. Any target with fewer than 30 test
positives after grouping is descriptive only and excluded from macro inference.
The scaffold-only component split is retained as a secondary sensitivity regime.

Fit activity thresholds, class weights, domain weights, label vocabularies, and
all learned preprocessing using training data only. Verify by invariant tests
that no canonical structure, scaffold, species, or component crosses partitions.

## Models and ablations

The compute-feasible confirmatory backbone is a radius-2, 2048-bit chiral Morgan
fingerprint feeding a two-layer MLP (1024, 512; ReLU; dropout 0.25). It has one
binary head per molecular target and one per auxiliary family. Missing labels
are masked in the loss.

| ID | Primary tasks | Ethnomedical tasks | Domain correction |
|---|---|---|---|
| ST | separate target models | no | no |
| MTL-P | shared encoder | no | no |
| MTL-E | shared encoder | yes | no |
| MTL-P-IW | shared encoder | no | importance weighting |
| MTL-E-IW | shared encoder | yes | importance weighting |
| MTL-E-PERM | shared encoder | permuted labels | no |

Select the auxiliary loss weight from {0.1, 0.3, 1.0} on validation macro
PR-AUC. Estimate importance weights with a training-only logistic classifier
that distinguishes ChEMBL molecules from natural products; clip density-ratio
weights to [0.2, 5.0]. Fit the classifier inside each split/seed.

Run seeds 13, 37, 71, 101, and 137. AdamW uses learning rate 3e-4 and weight
decay 1e-4, batch size 256, at most 100 epochs, and early stopping patience 12
on validation macro PR-AUC. No test-driven tuning is permitted.

Foundation encoders (ChemBERTa-2, MolFormer, or Uni-Mol2) are secondary
experiments. They must use identical data, split IDs, and heads. Their absence
does not invalidate the primary test of the ethnomedical prior.

## Endpoints and statistics

PR-AUC is primary because actives are rare. Report per-target and macro PR-AUC,
BEDROC with alpha 20, EF1%, ROC-AUC, Brier score, and prevalence. Report metrics
on (a) all eligible test molecules and (b) the natural-product subgroup.

The unit of resampling is the canonical molecule. Calculate paired differences
between MTL-E and MTL-P with 1,000 stratified bootstrap replicates and percentile
95% confidence intervals, preserving paired predictions. H1 is supported only
when the macro PR-AUC interval excludes zero in the favorable direction. Apply
Benjamini-Hochberg correction to target-level secondary comparisons.

For model selection, average validation results over five seeds. For the final
comparison, show each seed and the paired bootstrap interval; do not present the
best seed alone.

## Two-tier candidate validation

After the confirmatory analysis, screen VietHerb metabolites and select up to 20
candidates using a frozen rule combining calibrated model rank, applicability
domain, chemical diversity, and availability. Docking is a *post hoc orthogonal
check*, not ground truth. Record receptor structure choice, protonation, box,
software/version, exhaustiveness, and redocking RMSD. MD/MM-GBSA and enzyme
assays require a separate protocol and domain collaborator.

## Stop/go and reporting rules

- If authorized VietHerb structure/use edges cannot be obtained, publish neither
  the proposed title nor a synthetic substitute as the same study. Pivot to a
  protocol/data-access paper or use another licensed national-herbal database
  with a renamed scope.
- If fewer than two targets meet test-positive requirements, treat the work as a
  pilot rather than a multi-target confirmatory study.
- Report negative or null ablations. Do not remove targets based on test results.
- The manuscript's Results section is populated only from versioned output
  tables whose manifest hashes match the archived run.


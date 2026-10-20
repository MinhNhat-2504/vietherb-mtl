# Data contract

Raw and derived datasets are intentionally ignored by Git. Every real run must
write a manifest containing source URL, provider version, retrieval timestamp,
license/access note, SHA-256 checksum, row count, and the exact preparation
command.

## Canonical tables

### `molecules.parquet`

One row per standardized structure.

| Column | Type | Required | Meaning |
|---|---|---:|---|
| `molecule_id` | string | yes | Stable project ID derived from standard InChIKey |
| `canonical_smiles` | string | yes | Standardized isomeric SMILES |
| `inchikey` | string | yes | Standard InChIKey |
| `source` | string | yes | One of `chembl`, `vietherb`, `coconut`, `lotus`, `npass` |
| `source_id` | string | yes | Provider identifier |
| `is_natural_product` | bool | yes | Provenance-based domain flag |

### `activities.parquet`

Measured molecular-target activities only. Negative labels must be supported by
an explicit measurement; unmeasured pairs remain masked, not negative.

| Column | Type | Required | Meaning |
|---|---|---:|---|
| `molecule_id` | string | yes | Foreign key to molecules |
| `target_id` | string | yes | ChEMBL target ID |
| `pchembl_value` | float | yes | Curated potency on the -log10 molar scale |
| `active` | int | yes | Thresholded label using the frozen config |
| `standard_type` | string | yes | `IC50` or `Ki` in v1 |
| `assay_id` | string | yes | Source assay ID |
| `document_year` | int | no | Supports a future temporal sensitivity split |
| `contradictory` | bool | yes | Replicates spanning the contradiction margin |

### `ethnomed_labels.parquet`

Weak auxiliary labels propagated from a plant use to metabolites reported in
that species. These labels are not molecular bioactivity claims.

| Column | Type | Required | Meaning |
|---|---|---:|---|
| `molecule_id` | string | yes | Standardized metabolite |
| `species_id` | string | yes | Stable VietHerb species ID |
| `raw_use` | string | yes | Original therapeutic-use text |
| `term_id` | string | yes | Audited MeSH/ATC or project ontology ID |
| `weak_label` | int | yes | Usually one for observed use; absence stays masked |
| `mapping_method` | string | yes | `manual`, `lexical`, or named model/version |
| `mapping_confidence` | float | yes | Frozen mapper confidence, not efficacy probability |
| `review_status` | string | yes | `unreviewed`, `accepted`, or `rejected` |

At modelling time an auxiliary value of `1` means observed positive and `0`
means **unlabelled**, not negative. Auxiliary heads therefore use a
non-negative positive-unlabelled (nnPU) risk, not ordinary binary cross-entropy.

### `split_assignments.parquet`

| Column | Type | Required | Meaning |
|---|---|---:|---|
| `molecule_id` | string | yes | Molecule key |
| `split` | string | yes | `train`, `validation`, or `test` |
| `murcko_scaffold` | string | yes | Standardized scaffold key |
| `component_id` | string | yes | Connected component joining scaffold and species constraints |

## Annotation audit

`annotations/therapeutic_use_mapping.csv` is the version-controlled decision
table. Two domain reviewers should independently label a prespecified random
sample of 300 mappings. Report raw agreement and Cohen's kappa with a bootstrap
confidence interval. Adjudicate disagreements only after computing agreement.

Do not infer negative therapeutic labels from missing VietHerb entries. Missing
is represented as unlabelled and handled by the PU loss.


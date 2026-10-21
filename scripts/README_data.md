# Data acquisition and build runbook

This runbook documents the current scripts and the evidence needed for a
reproducible paper run. It does not grant permission to download or redistribute
any provider's data. Detailed source/legal notes are in
[`docs/data_sources.md`](../docs/data_sources.md).

No large dataset is committed to Git. Use these locations:

```text
data/raw/<source>/<release>/       immutable provider bytes/responses
data/interim/<source>/<release>/   validated, normalized source tables
data/processed/<dataset-version>/  frozen modelling artifacts
data/manifests/                    source locks and audit reports
```

## Before acquisition

1. Obtain written VietHerb permission for automated access, academic use,
   derivatives and redistribution. Record the message/terms in the run log.
2. Decide whether the paper artifact distributes data or only IDs/manifests.
   NPASS also lacks an explicit data licence, so exclude its rows from a public
   release without permission.
3. Freeze source versions in a proposed `data/manifests/sources.lock.yaml`.
4. Check free disk space before ChEMBL/COCONUT bulk downloads.

Minimum source-lock fields:

```yaml
source: chembl
release: 37
doi: 10.6019/CHEMBL.database.37
url: https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/...
retrieved_at_utc: YYYY-MM-DDTHH:MM:SSZ
license: CC-BY-SA-3.0
license_url: https://chembl.github.io/chembl-licensing/
filename: ...
bytes: ...
vendor_checksum: ...
sha256: ...
http_last_modified: ...
schema_hash: ...
```

Calculate a local SHA-256 even when a provider supplies MD5:

```powershell
Get-FileHash -Algorithm SHA256 data\raw\source\release\file.ext
```

```bash
sha256sum data/raw/source/release/file.ext
```

Do not overwrite a frozen directory. A changed upstream file gets a new
retrieval/version directory and manifest.

## ChEMBL

### Important configuration check

At audit time (2026-10-20), `configs/targets.yaml` said `chembl_release: 35`,
while the current versioned release was **ChEMBL 37**. Resolve and commit that
choice before confirmatory extraction. A REST response follows the live service
and does not become ChEMBL 35 merely because the config says 35.

For exploratory counts or a small auditable snapshot:

```powershell
python scripts/fetch_chembl.py `
  --config configs/targets.yaml `
  --out data/raw/chembl/live-api-2026-10-20
```

The fetcher writes one JSONL per target and a manifest with the config hash,
retrieval timestamp, row counts and file hashes. Use `--max-records` only for a
smoke test. These files are **not confirmatory-release data**.

For the paper, manually acquire the versioned ChEMBL 37 SQLite archive from:

```text
https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/
```

Verify the provider checksum and local SHA-256, decompress without modifying
the archive, then run:

```powershell
python scripts/extract_chembl_sqlite.py `
  --db data/raw/chembl/37/chembl_37.db `
  --config configs/targets.yaml `
  --out data/interim/chembl/37/activities.parquet
```

The exact SQLite filename can differ; use the name delivered by the release.
Check the generated manifest's database version rows and assert that they match
the config. Before freezing, audit by target: input/output records, unique
structures, activity types/relations/units, confidence scores, duplicate and
validity removals, censored values, conflicting replicates, positives and
scaffolds. The current extractor filters invalid/duplicate records but does not
fully implement all relation and organism/component assertions described in
the source audit; treat those as required acceptance checks.

## VietHerb

The live REST API is undocumented and the OWL download is incomplete. The
repository intentionally has no bulk scraper. After permission, either request
the original relational export from the maintainers or create a polite,
cached, UTC-dated REST snapshot outside the modelling step.

A REST snapshot must preserve raw JSON pages and these relations:

```text
plant/list + plant/info       -> species and species-use/metabolite edges
metabolite/list + info        -> metabolite identities and reverse plant edges
thera/list + info             -> therapeutic terms and reverse plant edges
files/VHO.owl                 -> ontology audit only, not the complete database
```

Reconcile edges from both directions, report discrepancies, and retain request
URLs, response headers, page totals, retries and SHA-256. Never infer a missing
edge from a failed page.

Transform the authorized snapshot/export to exactly:

```text
data/raw/vietherb/authorized-YYYY-MM-DD/species.csv
data/raw/vietherb/authorized-YYYY-MM-DD/metabolites.csv
data/raw/vietherb/authorized-YYYY-MM-DD/species_metabolites.csv
data/raw/vietherb/authorized-YYYY-MM-DD/species_uses.csv
```

Required headers are:

```text
species.csv:             species_id,scientific_name
metabolites.csv:         metabolite_id,name,smiles
species_metabolites.csv: species_id,metabolite_id
species_uses.csv:        species_id,raw_use
```

Additional provenance columns are allowed. Then validate and standardize:

```powershell
python scripts/ingest_vietherb.py `
  --input data/raw/vietherb/authorized-YYYY-MM-DD `
  --out data/interim/vietherb/authorized-YYYY-MM-DD
```

Inspect `rejected_structures.csv` and `manifest.json`. Do not use `--overwrite`
on a frozen run. The manifest's licence note must be replaced or accompanied by
the actual permission reference before release.

## BindingDB external-candidate audit

Download the October 2026 article-curated snapshot from the official BindingDB
download page. Do not use the combined BindingDB export because it includes
ChEMBL-sourced records. Place the provider bytes at:

```text
data/raw/bindingdb/BindingDB_BindingDB_Articles_202610_tsv.zip
```

Expected checksums:

```text
MD5     4b1d2f7c90e83dc6fd13e7b106a1f545
SHA-256 727383bac35beed6bc5c55c40dfbd58ba023fa97a7f27dc1a61440c1ad54a2b7
```

After extracting the TSV without modifying it, run the locked eligibility
audit:

```powershell
python scripts/audit_bindingdb_external.py `
  --bindingdb-zip data/raw/bindingdb/BindingDB_BindingDB_Articles_202610_tsv.zip `
  --bindingdb-tsv data/raw/bindingdb/BindingDB_BindingDB_Articles_202610_tsv/BindingDB_BindingDB_Articles.tsv `
  --chembl-activities data/interim/chembl/37/activities.parquet `
  --chembl-model-table data/processed/frozen_v1/model_table.parquet `
  --out data/processed/bindingdb_external_v1
```

The script verifies the source checksums and excludes ChEMBL 37 documents,
exact molecule overlap, contradictory pairs, and candidates with maximum
Tanimoto at least 0.70 to the modelling cohort. The paper eligibility decision
is frozen in `docs/manifests/bindingdb_external_audit.json`; candidate rows are
not model-scored when the three-target class-count gate fails.

## LOTUS

Pin version record `19360665` (2026-04-13), not only the moving concept DOI.
For the MVP, choose one:

- `260413_frozen.csv.gz` for the compact occurrence triples; or
- `260413_frozen_metadata.csv.gz` when structures/taxonomy descriptors are
  needed.

Acquire via the Zenodo record UI or its documented file-content endpoint:

```text
https://zenodo.org/api/records/19360665/files/260413_frozen.csv.gz/content
https://zenodo.org/api/records/19360665/files/260413_frozen_metadata.csv.gz/content
```

Verify both the Zenodo MD5 listed in `docs/data_sources.md` and a local SHA-256.
Save the record JSON alongside the file because it captures the version DOI,
date, licence and file metadata. Read only the header first and freeze a schema
report before full parsing. Normalize structures with the same versioned
pipeline as ChEMBL/VietHerb; retain the original InChIKey, organism Wikidata
QID, reference QID/DOI and manual-validation state.

No LOTUS importer is implemented in this repository yet. LOTUS is therefore an
optional provenance enhancement, not an implicit input to
`scripts/build_dataset.py`.

## COCONUT

The October 2026 full CSV is the smallest current export that includes
organism/collection/citation provenance. The lite CSV is acceptable only for
an unlabeled structure pool. Do not download the 31.91 GB SQL dump for the MVP.

Download manually from:

```text
https://coconut.naturalproducts.net/download
```

Pin the dated filename (`coconut_csv-10-2026.zip` or
`coconut_csv_lite-10-2026.zip`), bytes, retrieval UTC, HTTP metadata and local
SHA-256. The download page publishes no checksum. Preserve upstream collection
and citation columns to enforce source-specific licensing and leakage checks.
The authenticated live API is not suitable for a frozen paper dataset unless
every request/response and API version is captured.

No COCONUT importer is currently implemented. Membership is a domain flag, not
an activity label.

## NPASS

Use the NPASS-2026 download page and, at minimum, the structure, activity,
target, species-source and taxonomy archives:

```text
https://bidd.group/NPASS/downloadnpass.html
```

The provider does not publish checksums. Save the landing-page version, archive
filename, bytes/HTTP metadata and SHA-256. Validate the delivered headers rather
than assuming column names. Confirm joins and report orphan keys among `NPC...`
compound IDs, `NPT...` target IDs and species IDs.

Do not mix NPASS into training by default. NPASS 3.0 integrates ChEMBL 35, so
first remove any compound–target evidence matching ChEMBL by full InChIKey,
target accession/ChEMBL ID, document/reference and measurement. If a row's
provenance is ambiguous, it cannot count as independent external validation.
No NPASS importer is currently implemented, and raw rows must not be
redistributed without explicit permission.

## Therapeutic-use normalization

Freeze MeSH 2026 XML/RDF with the matching 2026 DTD, a tagged Mondo release,
and an NCBI Taxonomy snapshot. Record checksums and ontology versions. Keep the
raw VietHerb string and create decisions in
`data/annotations/therapeutic_use_mapping.csv` with the repository's header.

Recommended sequence:

1. Unicode and whitespace normalization only; keep a pointer to the raw text.
2. Exact synonym mapping to versioned MeSH/Mondo terms.
3. Human review of ambiguous, compound or malformed phrases.
4. If an LLM suggests candidates, store provider/model version, prompt hash,
   candidates and confidence; suggestions are never accepted automatically.
5. Two independent reviewers label the prespecified audit sample before
   adjudication; report agreement and Cohen's kappa.

An absent use is unlabelled, not negative. Propagation
`plant -> use -> all reported metabolites` creates weak positive evidence only.

## Build and acceptance gate

After a pinned ChEMBL extract and authorized VietHerb intermediate exist,
review `configs/dataset.yaml`, then run:

```powershell
python scripts/build_dataset.py --config configs/dataset.yaml
```

Before any experiment, the processed manifest must establish:

- exact raw/input and config hashes and all package/standardizer versions;
- target release and identity, structure rejection and deduplication counts;
- no identical full InChIKey across splits;
- no Murcko scaffold across splits;
- for VietHerb metabolites, no plant-species connected component across splits;
- no missing pair interpreted as inactive;
- target-wise measured/active/inactive/gray-zone counts and scaffold counts;
- separation of measured primary labels from weak auxiliary labels;
- train/validation/test assignment hash and deterministic seed;
- permission/licence record for every redistributed row.

Stop the paper run if a configured source release differs from the database
metadata, a required permission is absent, an input hash changes, or any split
invariant fails. Demo data may exercise software but must never appear in a
scientific result table.

# Data-source and licensing audit

Audit date: **2026-10-20**. This document separates what a web site makes
technically accessible from what it explicitly licenses for reuse. “Open
access”, “freely accessible”, and a paper's publication licence are not, by
themselves, permission to redistribute a database.

## Decision summary

| Source | Frozen version for a new run | Access | Licence / redistribution status | Role in MVP |
|---|---|---|---|---|
| VietHerb | UTC-dated REST snapshot plus `VHO.owl` | Public, undocumented REST; public OWL | **No explicit data licence found. Permission required before redistributing rows or a derived benchmark.** | Vietnamese plant–metabolite graph and weak therapeutic-use labels |
| ChEMBL | ChEMBL 37 (May 2026) | Versioned bulk DB and public REST API | CC BY-SA 3.0; attribution and share-alike apply | Primary measured target labels |
| LOTUS | Zenodo record `19360665`, 2026-04-13 | Versioned compressed CSV | Record metadata says CC BY 4.0; the live Wikidata/LOTUS layer is CC0 | Compound–organism provenance and references |
| COCONUT | October 2026 | Monthly ZIP/SQL downloads; authenticated API | Download page says CC0, but Terms preserve upstream contributor rights; retain collection-level provenance | Optional natural-product structure/domain pool |
| NPASS | NPASS 3.0 / NPASS-2026 | Bulk downloads; no documented public API | **No explicit database licence found. Do not redistribute without written permission.** | External NP activity/source audit, after leakage removal |
| Enveda ethnobotany | Pin a Git commit | Small files in GitHub | Repository MIT; incorporated upstream data retain their own terms | Optional cross-cultural plant–disease mappings |
| MeSH / Mondo | MeSH 2026; pinned Mondo release tag | XML/RDF/API; OWL/OBO/JSON | NLM terms; Mondo CC BY 4.0 | Controlled terminology, not activity ground truth |

The smallest defensible MVP is **VietHerb + ChEMBL 37 + LOTUS**. COCONUT adds
substantial download/storage cost without measured labels; NPASS partly imports
ChEMBL 35 and therefore is not an independent test set unless overlaps are
removed. Neither source is needed for the first experiment.

## 1. VietHerb

Primary links: [website](https://vietherb.com.vn/),
[paper](https://doi.org/10.1021/acs.jcim.8b00399), and
[PubMed record](https://pubmed.ncbi.nlm.nih.gov/30407009/).

### Availability and observed schema

The application is live. Its front end calls `https://vietherb.com.vn/api`.
The following public GET routes worked during this audit:

```text
/plant/list?page=1&pageSize=N&search=...
/metabolite/list?page=1&pageSize=N&search=...
/thera/list?page=1&pageSize=N&search=...
/plant/info?plantId=VH0001
/metabolite/info?metaboliteId=1
/thera/info?theraId=1
/plant/box-plot
/files/VHO.owl
```

The list envelope is:

```text
{success, status, message, total, page, pageSize, totalPages, data[]}
```

Observed entity fields are:

- plant: `id`, `plantEngName`, `plantVnName`, four image fields, `urlGbif`,
  `familiaId`, `genusId`, and nested `familia{id,family}` / `genus{id,genus}`;
- metabolite: `id`, `metaboliteName`, `CASID`, `inChiKey`, `SMILES`, `formula`,
  `linkPubchem`, `linkKnapsack`, `image`;
- therapeutic term: `id`, `theraName`;
- plant detail: the plant fields plus `morphologies[]`, `distributions[]`,
  `metabolites[]`, and `therapeuticEffects[]`;
- metabolite and therapeutic detail: the entity plus `plants[]`.

The live totals on 2026-10-20 were 2,828 plants, 10,239 metabolites, and 639
therapeutic-term records. These do **not** match the paper's first-release
figures of 2,881 species, 10,887 metabolites, 458 locations and 8,046
therapeutic effects. The paper also reports 17,602 species–metabolite and 2,718
species–effect edges. Treat the paper figures as historical, not validation
assertions for the live API.

The advertised ontology download is
[`VHO.owl`](https://vietherb.com.vn/api/files/VHO.owl). On the audit date it
returned 420,694 bytes with `Last-Modified: Thu, 25 Mar 2021 17:33:37 GMT` and
no ETag. It is a class-centric OWL ontology with properties such as
`meta:CAS_ID`, `meta:C_ID`, `meta:formula`, `meta:iupac_name`,
`meta:has_effect`, `effect:name`, `effect:from_herb`, `distribution`, and
`geo_coordinate`. Only six explicit `owl:NamedIndividual` declarations and
about 1,256 subclass statements were observed. It is therefore **not a complete
substitute for the live relational data**.

Data-quality checks are mandatory: blank or invalid SMILES occur, scientific
names are not guaranteed to be accepted taxonomic names, and therapeutic text
may concatenate several concepts. Preserve raw strings before normalization.

### Legal and reproducibility blocker

No data licence or terms granting redistribution were found on the site,
download response, OWL file, or paper. The paper calling the resource “open
source” does not establish a licence. The REST interface is undocumented and
has no stability or rate-limit contract.

This is **not a technical download blocker**: both REST and OWL were reachable.
It is a **release blocker** for a public benchmark containing VietHerb rows.
Request written permission from the maintainers (the site lists
`ly.le@hcmiu.edu.vn`) covering automated snapshotting, academic use, transformed
derivatives, and redistribution. Until then:

- use only a supplied/authorized export internally;
- publish code, source IDs, schemas, counts and hashes, not raw rows;
- do not claim the small OWL file is the full paper dataset;
- cache requests, identify the client, throttle, retry with backoff, and never
  bypass access controls.

For a frozen internal snapshot, save every response page verbatim, including
URL parameters and headers. Record UTC retrieval time, page count, entity/edge
counts, HTTP `Last-Modified`/ETag when present, per-file SHA-256, and a combined
manifest hash. Convert to the four authorized input tables expected by
`scripts/ingest_vietherb.py`:

```text
species.csv             species_id, scientific_name, ...
metabolites.csv          metabolite_id, name, smiles, ...
species_metabolites.csv species_id, metabolite_id, ...
species_uses.csv         species_id, raw_use, ...
```

## 2. ChEMBL

Primary links: [downloads and release DOIs](https://chembl.gitbook.io/chembl-interface-documentation/downloads),
[versioned FTP](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37/),
[REST documentation](https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services),
and [licensing](https://chembl.github.io/chembl-licensing/).

ChEMBL 37 was released in May 2026. Use the versioned bulk SQLite database for
confirmatory runs; the REST endpoint at `https://www.ebi.ac.uk/chembl/api/data/`
tracks the live service and is suitable only for exploration. Cite the release
DOI `10.6019/CHEMBL.database.37` after confirming it in the release metadata.
ChEMBL data content is CC BY-SA 3.0; include the ChEMBL URL and exact release in
attribution. The API client software licence does not replace the data licence.

### Tables and extraction schema

The relevant normalized join in the SQLite release is:

```text
target_dictionary td
  -> assays ass          via tid
  -> activities act      via assay_id
  -> molecule_dictionary md via molregno
  -> compound_structures cs via molregno
  -> docs d              via doc_id
  -> target_components / component_sequences for UniProt accessions
```

Retain, at minimum:

- identity: `md.chembl_id`, `cs.canonical_smiles`, `cs.standard_inchi`,
  `cs.standard_inchi_key`;
- activity: `activity_id`, `standard_type`, `standard_relation`,
  `standard_value`, `standard_units`, `pchembl_value`,
  `data_validity_comment`, `potential_duplicate`;
- assay: `assay_id`, `assay_type`, `confidence_score`, description;
- target: target ChEMBL ID, name, type, organism, taxon, component/UniProt ID;
- provenance: document ChEMBL ID, DOI/PubMed ID and year.

For primary labels select the frozen target IDs, `Homo sapiens`, `SINGLE
PROTEIN`, exact quantitative measurements, appropriate nM-compatible activity
types, high-confidence direct target assignments, no invalid records and no
duplicate flag. Preserve censored relations (`<`, `<=`, `>`, `>=`) rather than
silently treating all values as equality. ChEMBL defines pChEMBL only for a
controlled set of molar potency types; use its value where available and never
treat an unmeasured compound–target pair as inactive.

For the current three-task pilot, the repository uses CHEMBL284 (DPP4),
CHEMBL220 (AChE), and CHEMBL230 (PTGS2/COX-2). Verify target organism,
target type, component accession, and record depth against the pinned release
before freezing. Alpha-glucosidase and HCV NS3/NS5B require extra care because
names can resolve to multiple enzymes, organisms, complexes or assay contexts.

Versioning: retain the vendor checksum file when supplied, additionally compute
SHA-256 over the compressed archive and decompressed SQLite file, record exact
filename/byte count/release notes, and store the SQL text and row-count report.
Never use the `latest/` alias in a paper run.

## 3. LOTUS

Primary links: [LOTUS home](https://lotus.nprod.net/),
[eLife paper](https://doi.org/10.7554/eLife.70780), and
[Zenodo concept DOI](https://doi.org/10.5281/zenodo.5794106).

The concept DOI currently resolves to version record
[`19360665`](https://zenodo.org/records/19360665), dated 2026-04-13. Its files
and vendor MD5 values are:

| File | Bytes | Zenodo MD5 |
|---|---:|---|
| `260413_frozen.csv.gz` | 20,594,507 | `cf0cf2afa2ca4d758b68f2e39d466f5d` |
| `260413_frozen_metadata.csv.gz` | 90,298,678 | `b17048b3b77daae9ab1e480b6591aabd` |
| `260413_changes_report.txt` | 374 | `a166d5e34250254389f67605511005a3` |
| `lotus_exporter.py` | 106,800 | `af9209282f5e04586f22ed308cce66d7` |

The core file has one unique occurrence triple: structure InChIKey, organism
Wikidata QID and reference Wikidata QID, plus organism name, DOI and manual
validation state. The metadata file adds InChI/SMILES/formula/exact mass,
stereochemical descriptors, NPClassifier/ClassyFire, taxonomy, PubChem fields,
and publication identifiers. Validate exact column names from the downloaded
header because the exporter evolves.

The live LOTUS/Wikidata project describes its data as CC0. The cited frozen
Zenodo record itself declares **CC BY 4.0**; obey the licence attached to the
exact artifact used and cite its version DOI, not only the concept DOI. For the
MVP, use LOTUS for compound–organism–reference evidence, never as a molecular
target activity label. Join on standardized full InChIKey while retaining the
original structure and organism QID.

## 4. COCONUT

Primary links: [October 2026 downloads](https://coconut.naturalproducts.net/download),
[database schema](https://steinbeck-lab.github.io/coconut/db-schema.html),
[data documentation](https://steinbeck-lab.github.io/coconut/data.html),
[API documentation](https://steinbeck-lab.github.io/coconut/api-documentation.html),
and [terms](https://coconut.naturalproducts.net/terms-of-service).

The current page offers 2D lite/full SDF (287.6/691.7 MB), a 3D SDF (305.3
MB), a complete SQL dump (31.91 GB), and lite/full CSV ZIPs (191/207.9 MB).
The 3D coordinates are not minimized. The API is OpenAPI-based JSON but requires
registration/authentication; bulk files are preferable for a frozen run.

The molecule schema includes COCONUT identifier, names/CAS, standard InChI and
InChIKey, canonical and sugar-free SMILES, status/parent/stereo/tautomer flags,
Murcko framework, calculated physicochemical properties and chemical/NPClassifier
classes. Full exports additionally carry organisms, collections, citations,
DOIs and synonyms. The relational dump includes `molecules`, `structures`,
`properties`, `organisms`, `molecule_organism`, `collections`,
`collection_molecule`, `citations` and geolocation tables.

The download page declares the curated release CC0. The Terms also state that
contributors retain ownership and that COCONUT adds no restrictions beyond
original owners. Because those statements can differ for aggregated source
collections, preserve every collection/source field and exclude entries whose
upstream terms are incompatible with the intended public artifact. Ask the
maintainers when the provenance does not resolve the ambiguity.

For an MVP, either skip COCONUT or use the full CSV only as an unlabeled
natural-product pool; the lite CSV omits organism provenance. Pin the dated
filename (`*-10-2026.zip`), URL, HTTP metadata and bytes, and calculate SHA-256
because the page does not publish a cryptographic manifest. Do not label
“present in COCONUT” as active.

## 5. NPASS

Primary links: [NPASS home](https://bidd.group/NPASS/index.php),
[NPASS-2026 downloads](https://bidd.group/NPASS/downloadnpass.html),
[about/data model](https://bidd.group/NPASS/about.php), and
[NPASS 3.0 paper](https://doi.org/10.1093/nar/gkaf1196).

NPASS 3.0 reports 204,023 natural products, 48,940 organisms, 8,764 targets and
1,048,756 activity records. The download page provides 11 archives: compound
general information, structures, activities, species sources, targets,
taxonomy, toxicity, and four specialized organism/source files. It publishes
approximate sizes but no checksums. No documented public REST API was found.

Expected logical keys/fields, to be confirmed from archive headers, are:

- compound: NPASS `NPC...` ID, names, external identifiers, standard InChI,
  InChIKey and canonical SMILES;
- target: `NPT...` ID, name/type/organism and external ChEMBL/UniProt links;
- activity: compound ID, target ID, activity type, relation/value/unit,
  reference and molecular/in-vitro/in-vivo level;
- source: compound–organism pair, NCBI taxon, plant part/location/date and
  reference; plus a separate taxonomy table.

NPASS says it is freely accessible, but no explicit database licence or reuse
terms were located. Treat it as permission-required for redistributed data or
derived row-level benchmarks. Compute SHA-256, byte count and header schema for
each downloaded archive and retain the download time/version. The current
NPASS activities incorporate ChEMBL 35, so deduplicate compound–target–assay or
reference evidence against ChEMBL before any “external” evaluation. Prefer a
strictly manual-literature subset if provenance permits; otherwise report NPASS
only as a sensitivity analysis, not independent validation.

## 6. Auxiliary ethnopharmacology resources

The [Enveda ethnobotany repository](https://github.com/enveda/ethnobotany)
accompanies [Domingo-Fernández et al.](https://doi.org/10.1016/j.isci.2023.107729)
and includes `plant_disease_associations.tsv.gz` (1.11 MB),
`plant_disease_collapsed.tsv.gz` (1.25 MB),
`plant_chemical_associations.tsv.zip` (5.77 MB), geolocation data, and two
non-binary association matrices. The latter are wide disease-by-plant matrices:
the row key is a disease/Mondo concept, plant columns use NCBI Taxon IDs, and
cells retain citation sets rather than simple binary truth. The long-form files
and exact headers must be schema-inspected at the pinned commit before use.
These files were assembled from VietHerb, LOTUS, COCONUT and other databases.
Pin a commit SHA, hash each file, and retain its NCBI Taxon, disease ontology
and citation provenance. The repo is MIT-licensed, but that cannot expand
rights in embedded upstream records; apply the original source terms row by
row. It is useful for mapping/robustness, not an independent test set because
it already contains VietHerb-derived evidence.

Normalize disease/use text against:

- [MeSH downloads](https://www.nlm.nih.gov/databases/download/mesh.html): pin
  production year 2026 and matching DTD; XML or RDF is preferred because ASCII
  ended in January 2026. Use is subject to the linked NLM terms.
- [Mondo downloads](https://mondo.monarchinitiative.org/pages/download/): pin a
  GitHub release asset/tag in OWL, OBO or JSON; licence CC BY 4.0.
- [NCBI Taxonomy](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/data-processing/taxonomy-processing/taxonomy/):
  freeze a `new_taxdump`/Datasets snapshot for scientific names, synonyms,
  ranks and lineages.

MeSH/Mondo are vocabularies for normalization, **not labels**. Preserve
`raw_use`; normalize Unicode/whitespace; map exact curated synonyms first;
store every candidate and rejection; and have two reviewers independently
audit a prespecified sample before adjudication. Store ontology ID/version,
mapping method/model/prompt hash, confidence, reviewer status and citation.
ATC is a drug classification rather than a disease ontology and is excluded
from MVP therapeutic-use mapping.

## 7. Canonical MVP schema and leakage controls

Keep source-specific raw tables immutable, then materialize these normalized
relations:

```text
compound(compound_id, source, source_compound_id, canonical_smiles,
         standard_inchi, full_inchikey, connectivity_key,
         standardization_status, provenance_ref)
organism(organism_id, source, source_organism_id, scientific_name_raw,
         accepted_name, ncbi_taxid, rank, family, genus, taxonomy_status)
compound_organism(compound_id, organism_id, evidence_source, reference_id,
                  plant_part, manual_validation)
ethno_term(ethno_term_id, text_raw, language, normalized_text)
ethno_mapping(ethno_term_id, ontology, ontology_id, label, mapping_method,
              confidence, reviewer_status, ontology_version)
organism_ethno(organism_id, ethno_term_id, source, reference_id)
target(target_id, chembl_target_id, uniprot_id, name, organism, target_type)
activity(activity_id, compound_id, target_id, standard_type, relation, value,
         units, pchembl_value, assay_id, assay_type, confidence_score, doc_id,
         year, validity, duplicate_flag, source_release)
weak_label(compound_id, label_id, via_organism_id, support_count, source)
split(compound_id, split_name, fold, grouping_key, seed, dataset_hash)
```

Weak labels arise only through
`plant -> reported therapeutic use` and `plant -> reported metabolite`. This
many-to-many join is a prior with positive/unlabelled semantics; it is not
evidence that the metabolite treats the disease or binds a target.

For measured labels, aggregate comparable ChEMBL replicates after relation/unit
checks. A practical prespecified classification has active `pChEMBL >= 6`,
inactive `pChEMBL <= 5`, and excludes the gray interval; an alternative single
threshold is acceptable only if frozen before test evaluation. Missing pairs
remain masked. Always report continuous-potency sensitivity analyses.

Deduplicate by standardized full InChIKey for labels; retain the connectivity
block separately for analog/leakage checks and never silently merge
stereoisomers. Assign all identical compounds, Murcko scaffolds, and (for the
VietHerb subset) plant-species components to one split. COCONUT, LOTUS, NPASS
and Enveda share upstream sources, so “database-disjoint” does not imply
evidence-disjoint: compare original collection/reference IDs too.

Every source lock entry must contain source name, exact release/DOI, immutable
URL, retrieval UTC, licence URL/status, expected bytes/vendor checksum,
locally computed SHA-256, HTTP metadata, query parameters, schema/header hash,
row counts and extractor Git commit. Every derived manifest additionally stores
raw hashes, config hash, RDKit/standardizer versions, transformation counters,
null/unique statistics, split seed and output hash.

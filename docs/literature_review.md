# Literature, novelty, and experimental-design review for Topic 2

**Working topic:** *Ethnopharmacology-informed multi-task learning for multi-target screening of Vietnamese medicinal-plant metabolites*

**Review cut-off:** 20 October 2026

**Purpose:** stress-test the claims in the proposal PDF, identify the closest prior art, and turn the idea into a defensible Q1-paper design.

## 1. Executive assessment

The project remains publishable, but the novelty must be stated more narrowly than in the proposal.

**Verified fact.** The original VIETHERB article reports 2,881 species, 10,887 metabolites, 458 geographical locations, 8,046 “therapeutic effects,” 17,602 species–metabolite relationships, and 2,718 species–therapeutic-effect relationships ([Nguyen-Vo et al., 2019](https://doi.org/10.1021/acs.jcim.8b00399)). The database and its Vietnamese focus are genuine assets.

**Correction.** It is no longer defensible to say that previous work on this general problem is mainly single-task classification, or that no one has used traditional-use/clinical-phenotype knowledge to support molecular-target prediction. By the review cut-off:

- HTINet already incorporated herbal efficacy and herb–disease/symptom associations into a heterogeneous network for supervised herb–target prediction ([Wang et al., 2019](https://doi.org/10.1016/j.csbj.2019.02.002)).
- HTINet2 used TCM-property and clinical-treatment knowledge in a knowledge graph for supervised herb–target prediction ([Duan et al., 2024](https://doi.org/10.1093/bib/bbae414)).
- Multi-ITI combined molecular and network modalities for herbal ingredient–target prediction ([Liang et al., 2025](https://doi.org/10.1016/j.ins.2025.122115)).
- NovelHTI predicted protein targets directly from standardized clinical symptom profiles of herbs, including strict cold-start tests ([Cheung, 2026](https://doi.org/10.3390/ph19030413)).
- SM-GAT jointly modeled DPP4, alpha-glucosidase, and toxicity endpoints and screened a TCM natural-product library ([Zhang et al., 2026](https://doi.org/10.3389/fmolb.2026.1854162)).
- ProDTI introduced prior-guided positive–unlabeled learning for DTI prediction ([Wang et al., 2026](https://doi.org/10.1093/bioinformatics/btag712)).

**Defensible novelty (inference from the search, not a proof of absence).** A plausible contribution is the first openly reproducible study to treat *Vietnamese herb-level traditional-use annotations as noisy bag-level supervision for compound-level, experimentally measured target activity*, with leakage-controlled evaluation on unseen chemistry and unseen botanical sources. The key methodological distinction is hierarchical/multiple-instance weak supervision: a plant’s reported use does not imply that every recorded metabolite is active. The paper should say “to our knowledge, after the search described below,” never “no one has done this.”

**Recommended core claim.** The main scientific question should be:

> Does correctly modeled, herb-level ethnopharmacological supervision improve out-of-distribution ranking of Vietnamese natural products for measured molecular-target activity beyond gains due merely to more labels, chemical similarity, plant identity, or model capacity?

This is stronger than “we fine-tuned a modern backbone,” which is an engineering choice rather than a scientific contribution.

## 2. Search boundary and claim discipline

The review covered combinations of *ethnopharmacology/traditional use/herb symptom/clinical indication*, *weak supervision/multiple-instance learning/multi-task learning*, and *drug-target/compound-target prediction*, plus direct searches for VIETHERB, Vietnamese traditional-medicine knowledge graphs, the proposed targets, data-splitting practice, and the candidate journals. Publisher pages, PubMed/PMC, official database documentation, WHO sources, and primary papers were preferred. Searches were performed through 20 October 2026.

An absence claim can still be overturned by terminology differences, non-English literature, or an unindexed preprint. Therefore:

- **Fact** below means directly supported by a linked primary or authoritative source.
- **Inference** means a design conclusion or a bounded novelty judgment based on the located evidence.
- **To verify in data** means the paper claim must wait for a reproducible audit of the downloaded dataset.

## 3. Audit of the proposal PDF

| Proposal claim | Status | Evidence and required revision |
|---|---|---|
| VIETHERB contains 10,887 metabolites and 8,046 therapeutic effects. | **Fact, but semantically ambiguous.** | These numbers appear in the original article ([DOI](https://doi.org/10.1021/acs.jcim.8b00399)). However, that article also reports only 2,718 species–therapeutic-effect binary relations. Do not interpret “8,046 therapeutic effects” as 8,046 independent, compound-level labels. Audit the ontology dump and report unique concepts, text strings, occurrences, and edges separately. |
| Existing VIETHERB use is mainly single-task classification. | **Unsupported as written.** | The proposal should cite the actual downstream VIETHERB studies it found and define what “use” means. More importantly, adjacent TCM work now contains multi-task, graph, and phenotype-to-target approaches. |
| No prior work uses traditional-use labels as weak supervision for molecular targets. | **Too strong / likely false at the broad level.** | HTINet uses efficacy and herb–disease/symptom relations for herb-target prediction; NovelHTI uses clinical symptom profiles to infer targets; HTINet2 incorporates clinical-treatment knowledge; SM-GAT uses traditional indications as external knowledge-based validation. The narrower *herb-bag label -> compound encoder auxiliary loss -> measured compound-target task* formulation was not found in this search and may remain novel. |
| Map 8,046 descriptions to MeSH/ATC using an LLM. | **Needs correction.** | MeSH is a controlled indexing thesaurus ([NLM](https://www.nlm.nih.gov/mesh/meshhome.html)); ATC classifies active drug substances by anatomical, therapeutic, pharmacological, and chemical properties ([WHO](https://www.who.int/tools/atc-ddd-toolkit/atc-classification)). ATC is not a disease/indication ontology and is a poor primary target for free-text traditional-use normalization. Prefer a two-layer representation: observed use/symptom -> MeSH and/or UMLS/SNOMED; disease concept -> Mondo/DOID/ICD. Keep the original Vietnamese text and mapping confidence. |
| Random expert validation of 300 mappings and Cohen's kappa is sufficient. | **Incomplete.** | Estimate required sample size by expected prevalence and desired CI. Use two independent domain annotators, adjudication, concept-level exact/ancestor-aware precision, recall, F1, and inter-annotator agreement. Kappa alone can be misleading under skew. Freeze a stratified gold test set before prompt/model iteration. |
| Scaffold split plus plant-species split prevents leakage. | **Directionally correct, underspecified.** | Exact compounds and near-neighbors can cross distinct scaffolds, and the same metabolite may occur in multiple species. Use globally deduplicated molecules, a structure-cluster OOD split, and a separate botanical cold-start split; quantify nearest-neighbor similarity after splitting. Scaffold splits can still be optimistic ([Guo et al., 2024 preprint](https://arxiv.org/abs/2406.00873); [Fooladi et al., 2025](https://doi.org/10.1021/acs.jcim.5c00475)). |
| PR-AUC, BEDROC(alpha=20), and EF1% are appropriate. | **Yes, with additions.** | PR curves are useful for imbalanced problems ([Saito & Rehmsmeier, 2015](https://doi.org/10.1371/journal.pone.0118432)); BEDROC was designed for early recognition ([Truchon & Bayly, 2007](https://doi.org/10.1021/ci600426e)). Report prevalence, AUROC secondarily, calibration, per-target and macro results, paired CIs, and EF at an absolute budget as well as a percentage. |
| Docking + 50–100 ns MD + MM-GBSA validate the top 20. | **Overstated.** | They provide orthogonal computational prioritization, not biological validation. A large docking benchmark found no useful affinity ranking from the tested scoring functions ([Warren et al., 2006](https://doi.org/10.1021/jm050362n)); MM/GBSA has system-dependent limitations ([Hou et al., 2011](https://doi.org/10.1021/ci100275a); [Genheden & Ryde, 2015](https://doi.org/10.1517/17460441.2015.1032936)). Call this “structure-based plausibility assessment.” An in-vitro assay is the independent validation. |
| Domain-adversarial training or importance weighting will correct the natural-product distribution shift. | **Hypothesis, not established fact.** | Include these only after measuring the shift and overlap. Compare against simple reweighting and no-adaptation controls; domain invariance can remove activity-relevant signal. |
| COCONUT, LOTUS, and NPASS are interchangeable supplementary sources. | **False.** | They play different roles. COCONUT and LOTUS mainly support natural-product structure/occurrence coverage; NPASS includes quantitative activity and species-source data. Their records can overlap with one another and with ChEMBL, so source-aware deduplication is mandatory. |
| Sanjeevani (2026) is an appropriate comparison. | **Verified, but only partially relevant.** | Sanjeevani is a June 2026 bioRxiv preprint and cancer-specific database/tool with 4,823 curated anticancer phytochemicals ([preprint](https://doi.org/10.64898/2026.06.15.732344)). Compare resource documentation and screening workflow, but not target-task performance unless the present paper adds an oncology endpoint under identical data. |
| The proposed journals are Q1 and suitable. | **Quartile depends on year/category; fit differs sharply.** | SCImago showed Q1 placements for Journal of Cheminformatics and Journal of Ethnopharmacology in its 2024 data, but quartiles must be rechecked at submission. Scope and evidence level, not quartile alone, should determine the target. |

## 4. Closest prior work and the remaining gap

### 4.1 Directly adjacent computational ethnopharmacology

1. **Traditional classes and phenotypes have already been connected to targets.** A global TCM mapping study linked predicted targets and pathways to therapeutic-action subclasses ([Mohamad Zobir et al., 2016](https://doi.org/10.1155/2016/2106465)). HTINet incorporated herbal efficacy and herb–disease/symptom associations into a heterogeneous network for supervised herb-target prediction ([Wang et al., 2019](https://doi.org/10.1016/j.csbj.2019.02.002)). NovelHTI later made clinical symptom profiles the input for inductive herb-target prediction ([Cheung, 2026](https://doi.org/10.3390/ph19030413)). Therefore, “traditional knowledge as a molecular prior” is not itself new.

2. **Herb-targets and symptoms have also been joined in the reverse direction.** Gan et al. mapped known herb targets and symptom-associated proteins to the human interactome, showed that network proximity predicts herb–symptom effectiveness, and validated the relationship with hospital patient data ([Gan et al., 2023](https://doi.org/10.1126/sciadv.adh0215)). This does not train compound-level activity predictors, but it is strong prior art for the biological premise linking traditional symptom labels to molecular mechanisms.

3. **Herb/ingredient-target graphs are mature baselines.** HTINet2 uses knowledge-graph embedding, a residual-like GNN, and supervised ranking ([Duan et al., 2024](https://doi.org/10.1093/bib/bbae414)). Multi-ITI integrates molecular sequences, protein sequences, similarities, and interaction-network topology while explicitly addressing noisy literature-mined edges ([Liang et al., 2025](https://doi.org/10.1016/j.ins.2025.122115)). A critical review documents that TCM databases often mix experimentally validated and computationally inferred targets, which can produce circular evaluation ([Wang et al., 2024](https://doi.org/10.3389/fphar.2024.1303693)).

4. **The proposed diabetes pair is already occupied.** SM-GAT jointly learns DPP4, alpha-glucosidase, oral toxicity, and clinical toxicity and screens TCMBank natural products ([Zhang et al., 2026](https://doi.org/10.3389/fmolb.2026.1854162)). It reported a larger multi-task gain on the smaller alpha-glucosidase task than on DPP4, but acknowledged the need for scaffold/temporal validation. Repeating DPP4 + alpha-glucosidase with another backbone and VIETHERB would be an application paper, not a strong methodological novelty claim.

5. **Traditional attributes have been learned from phytochemistry.** SitoshnaPred predicts Ayurvedic hot/cold/neutral potency from phytochemical descriptors ([DOI](https://doi.org/10.1016/j.jep.2025.120620)). Yoo et al. predicted medicinal uses of plant-derived compounds using heterogeneous molecular, interaction, and literature features ([DOI](https://doi.org/10.3389/fphar.2020.584875)). These establish both directions of the phenotype–chemistry bridge.

6. **Vietnamese knowledge resources now extend beyond VIETHERB.** VietMedKG is a Vietnamese traditional-medicine knowledge graph and QA benchmark, although its task is QA and it adapts TCM resources rather than predicting measured compound-target activity ([Trinh et al., 2025](https://doi.org/10.1145/3744740); [code](https://github.com/HySonLab/VietMedKG)). It must be discussed to avoid claiming that VIETHERB is the only computational TVM resource.

### 4.2 General multi-task and label-learning precedents

- Multi-task bioactivity prediction is established. Large-scale studies have shown benefits but also negative transfer; grouping related targets and knowledge distillation can be better than training every target together ([Moon & Kim, 2022](https://doi.org/10.1038/s41598-022-23203-y)).
- D-MPNN/Chemprop remains a strong, reproducible learned-representation baseline and often benefits from RDKit descriptors ([Yang et al., 2019](https://doi.org/10.1021/acs.jcim.9b00237)). A fingerprint model must also be included.
- Missing interactions are not verified negatives. Positive–unlabeled approaches are established in computational biology ([PU-learning review](https://doi.org/10.1093/bib/bbab461)) and DTI prediction ([Cheng et al., 2018](https://doi.org/10.1109/TCBB.2016.2570211)); the very recent ProDTI raises the expected baseline standard ([Wang et al., 2026](https://doi.org/10.1093/bioinformatics/btag712)).

### 4.3 The gap that can still be claimed

**Inference.** The distinguishing problem in VIETHERB is label granularity. Therapeutic effects are attached to a plant species, while molecular-target measurements are attached to individual compounds. Broadcasting a plant label to all its listed metabolites creates false labels and confounds botanical identity with chemistry.

The paper can make a methodological contribution by formulating the data as:

- a **bag** = a medicinal plant species;
- **instances** = standardized metabolites reported for that species;
- a **bag label** = curated traditional-use/disease/symptom concept;
- an **instance label** = measured target activity from ChEMBL, where available;
- a shared molecular encoder trained by masked target losses plus an attention/noisy-OR multiple-instance loss at plant level;
- optional positive–unlabeled treatment for unmeasured compound-target pairs.

This formulation does not assume that every constituent causes the reported effect, permits interpretable attribution of a bag prediction to candidate compounds, and creates a clean ablation against naive label broadcasting. Multiple-instance learning is not new generally, including in drug-activity prediction ([Doran & Ray, 2012](https://doi.org/10.1186/1471-2105-13-S15-S3)), but its use for this cross-granularity Vietnamese ethnopharmacology problem was not found in the bounded search.

## 5. Recommended target scope

### 5.1 Disease relevance

**Fact.** Vietnam’s WHO STEPS 2021 report estimated raised fasting glucose or diabetes treatment in 7.1% of adults aged 18–69, up from 4.1% in 2015 ([WHO report, ISBN 978-92-9-062026-6](https://www.who.int/westernpacific/publications/i/item/9789290620266)). Diabetes is therefore a well-supported local-health rationale.

**Fact.** A 2025 WHO information sheet estimated chronic HBV prevalence in Vietnam at 7.2% and HCV prevalence at 0.9% ([WHO Western Pacific viral-hepatitis information sheet](https://cdn.who.int/media/docs/default-source/hq-hiv-hepatitis-and-stis-library/2025-whd-hep-information-sheet.pdf)). NS3 and NS5B are HCV targets, not generic “hepatitis” targets. Calling them simply hepatitis targets is scientifically inaccurate, and an HCV-only emphasis misses the much larger HBV burden.

**Fact.** AChE inhibition is a recognized symptomatic strategy in Alzheimer disease, while COX-2 is a broad inflammation target rather than a disease-specific endpoint. Their local relevance should not be asserted without Vietnam-specific evidence.

### 5.2 Practical recommendation

Run a data audit before fixing the target panel. A three-target first paper is easier to interpret and power than a heterogeneous five-target collection.

Recommended starting panel:

1. **DPP4 (human; ChEMBL CHEMBL284):** strong diabetes rationale and ample public activity data.
2. **AChE (human; CHEMBL220):** chemically and biologically distinct from DPP4, useful for testing whether the ethnopharmacology prior transfers across therapeutic areas.
3. **COX-2/PTGS2 (human; CHEMBL230):** data-rich inflammatory endpoint, but traditional-use mapping must distinguish pain, fever, and inflammation rather than collapsing them.

Conditional endpoint:

- **Human intestinal alpha-glucosidase:** specify the protein (e.g., maltase-glucoamylase, MGAM/CHEMBL2074, or sucrase-isomaltase) and do not pool yeast, rat, unknown-organism, and human assays. The phrase “alpha-glucosidase” spans different enzymes and assay systems. Add it only if the post-curation human dataset is sufficiently large. Because SM-GAT already used the DPP4/alpha-glucosidase pair, it cannot carry the novelty.

Defer NS3/NS5B unless the study is redesigned as an HCV-specific module with genotype, viral protein, assay, and treatment-context controls. Mixing viral proteins with unrelated human enzymes in one hard-shared model is an invitation to negative transfer.

## 6. Data construction and leakage controls

### 6.1 VIETHERB audit before modeling

The following are **to verify in data** and should become a versioned data report:

1. Download/export provenance, date, license/terms, file hashes, and whether the online release differs from the 2019 paper.
2. Counts of unique accepted plant names, synonyms, unresolved taxa, metabolites, valid structures, therapeutic-effect strings, normalized concepts, and each edge type.
3. Taxonomic resolution against an authoritative backbone; retain original names and mapping confidence.
4. Molecular standardization: remove mixtures and invalid structures; normalize salts/charges/tautomers according to a frozen protocol; preserve stereochemistry; deduplicate by standard InChIKey with a documented stereochemical policy.
5. Many-to-many structure: distribution of compounds per species, species per compound, effects per species, and connected components in the species–metabolite graph.
6. Explicit reconciliation of “8,046 therapeutic effects” versus 2,718 species–effect relations.

### 6.2 Traditional-use normalization

Do not let an LLM directly create final labels. Use retrieval-constrained normalization:

1. Preserve source text and language.
2. Retrieve candidates from a frozen ontology release and synonym index.
3. Let the model rank candidates and output `concept_id`, confidence, evidence span, and abstention.
4. Require a domain expert to review all high-impact mappings and a stratified sample of the remainder.
5. Store mappings as versioned data with the prompt/model/version and adjudication trail.

Prefer MeSH/UMLS/SNOMED for symptoms and clinical phrases and Mondo/DOID/ICD for disease concepts. ATC may be used later to group reference drugs, not as the primary disease ontology.

### 6.3 ChEMBL endpoint curation

Use a frozen release; the official download page listed ChEMBL 36 (July 2025; DOI [10.6019/CHEMBL.database.36](https://doi.org/10.6019/CHEMBL.database.36)) at the review cut-off.

Minimum curation rules:

- exact target identifiers and organism; single-protein targets unless a separate complex endpoint is intended;
- explicit assay type and relationship; do not silently combine binding, functional, cellular, and organism assays;
- harmonized standard types and units; retain censored relations (`<`, `>`) rather than coercing them to exact values;
- remove data-validity warnings and low-confidence target assignments;
- aggregate replicates using a documented rule and flag contradictory measurements;
- avoid treating “not measured” as inactive;
- define activity thresholds before test evaluation and run sensitivity analyses at plausible cutoffs;
- publish a flow diagram and per-target counts after every filter.

Where data permit, continuous pActivity modeling with censored observations is preferable to throwing away the gray zone. If binary classification is used, one reasonable primary threshold can be pChEMBL >= 6 (1 micromolar), but it is not a universal truth and should be justified per target.

### 6.4 Roles of the proposed natural-product databases

- **COCONUT 2.0** is an aggregated, downloadable natural-product structure resource with organism and literature annotations where available; its authors explicitly note that errors inherited from source databases remain possible ([Chandrasekhar et al., 2025](https://doi.org/10.1093/nar/gkae1063)). Use a frozen release to characterize or expand chemical space, not as automatically trusted activity ground truth.
- **LOTUS** is a community-curated structure–organism occurrence resource hosted through Wikidata and Natural Products Online ([Rutz et al., 2022](https://doi.org/10.7554/eLife.70780)). It is useful for independent provenance checks and taxonomic occurrence, provided references are retained.
- **NPASS 2026** contains quantitative composition, activity, and ADME-Tox data ([Zhao et al., 2026](https://doi.org/10.1093/nar/gkaf1196)). It can provide external activity/provenance evidence, but experimentally derived and computationally estimated records must remain distinguishable. Check for document/assay overlap with ChEMBL before calling it external validation.
- **Sanjeevani** is a cancer-focused preprint resource, not a general ethnopharmacology baseline ([Jha et al., 2026](https://doi.org/10.64898/2026.06.15.732344)).

For every imported record, retain `source_database`, `source_version`, primary-reference identifier, evidence type, and original record ID. Merge on standardized structure only after preserving provenance.

### 6.5 Splits answer different scientific questions

Use at least two locked external test regimes:

1. **Chemical OOD:** split standardized molecules by structure clustering (e.g., Butina or another predeclared method), not only Bemis–Murcko scaffolds. Allocate each molecule globally so it cannot cross splits through another target or plant. Report train–test nearest-neighbor Tanimoto distributions and exact/scaffold overlap.
2. **Botanical cold start:** hold out plant species, genera, or families and all their exclusive bag labels. Shared metabolites must be handled explicitly: either remove them from the cold-start test, place the molecule globally in one split, or report a “shared-metabolite” stratum separately.

A chronological ChEMBL split is preferable when reliable publication/deposition dates are available because it approximates prospective use ([Sheridan, 2013](https://doi.org/10.1021/ci400084k)). Random splits may be included only as an optimistic diagnostic. Benchmark redundancy can make ligand classifiers reward memorization ([Wallach & Heifets, 2018](https://doi.org/10.1021/acs.jcim.7b00403)).

The mapping gold set, model validation set, and final test set must be disjoint. All models and ablations must use the same split manifests.

## 7. Model and baseline matrix

The experiment should isolate the value of ethnopharmacology, not just compare model brands.

| Family | Required model/control | Purpose |
|---|---|---|
| Classical | Morgan/ECFP + logistic regression; Morgan/ECFP + random forest or XGBoost | Strong low-cost baselines; exposes whether deep learning is needed. |
| Single-task neural | D-MPNN/Chemprop trained separately per target | Controls parameter sharing. |
| Standard multi-task | Same molecular encoder and heads, masked target loss only | Measures target-to-target transfer without traditional knowledge. |
| Grouped multi-task | Targets grouped by ligand-set/target similarity, optionally with distillation | Controls known negative-transfer mitigation from Moon & Kim. |
| Pretrained encoder | One frozen or fine-tuned molecular foundation model (e.g., MolFormer, [Ross et al., 2022](https://doi.org/10.1038/s42256-022-00580-7)) | Tests whether pretraining removes the auxiliary-label benefit. Do not include several expensive backbones unless compute permits full repeats. |
| Proposed | Shared compound encoder + target heads + species-bag MIL ethnopharmacology head | Tests the actual hypothesis. |
| PU variant | Target loss treating unknowns as unlabeled rather than negatives | Sensitivity to missing-negative bias. |

Mandatory ablations and falsification tests:

- remove the ethnopharmacology loss;
- naive broadcast of plant labels to all metabolites versus MIL aggregation;
- shuffle effect labels among plants while preserving label frequency;
- replace ethnopharmacology with equally sized random auxiliary labels;
- ontology-mapped labels versus coarse manually defined therapeutic systems;
- expert-verified mappings only versus all confidence-weighted mappings;
- remove plant identity/taxonomic features, if any;
- equalize parameter count and number of training updates;
- vary the auxiliary-loss weight and report task-wise negative transfer;
- compare domain adaptation with no adaptation and simple importance weighting.

The shuffled-label and naive-broadcast controls are especially important. Without them, a gain may come from regularization, sample duplication, plant identity, or chemical-family leakage rather than meaningful traditional knowledge.

## 8. Metrics and statistical analysis

### 8.1 Primary predictive metrics

- **AUPRC per target** as the primary classification metric, with test prevalence shown beside it. Because the random baseline equals prevalence, do not compare raw AUPRC across targets without context.
- **BEDROC(alpha=20)** and **EF1%/EF5%** for early retrieval. Also report recall/precision at a realistic absolute experimental budget (for example top 20 or top 50), since 1% means different numbers for different libraries.
- **AUROC** as a secondary global-ranking metric.
- **Brier score and a calibration curve** (or ECE with binning specified) if scores will guide experimental decisions.
- For continuous activity: MAE/RMSE plus Spearman; use concordance methods if censored observations are modeled.
- For the plant-bag task: macro AUPRC plus Recall@K/NDCG@K for held-out species or effects.

### 8.2 Estimation and testing

- Predeclare one primary model comparison and one primary aggregate endpoint.
- Use at least five independently trained seeds on identical split manifests.
- Report paired differences with 95% confidence intervals from a bootstrap whose resampling unit respects dependence (preferably structure cluster; species for bag-level evaluation).
- Report every target, not only the macro average. A multi-task model can improve the mean while harming specific tasks.
- Correct inferential p-values across target/metric families if many hypotheses are tested.
- Include learning curves to show whether the prior helps mainly in low-data regimes.
- Measure applicability domain with nearest-neighbor similarity and uncertainty, not t-SNE alone.

## 9. Validation ladder

### Tier 1: retrospective checks

- Evaluate docking against known actives/inactives or decoys before docking novel VIETHERB hits.
- Redock a cognate ligand and report pose RMSD where a suitable crystal structure exists.
- Use consistent protonation, receptor-state, water/cofactor, and box protocols.
- Check whether the ML top ranks enrich held-out measured actives; this is more important than agreement with a second computational score.

### Tier 2: structure-based plausibility

Docking and short MD/MM-GBSA can test pose stability and identify implausible candidates. They should not be called validation of target inhibition, and ML–MM/GBSA rank correlation is not a primary success metric because neither prediction is experimental ground truth.

### Tier 3: prospective experimental validation

For a Q1 ethnopharmacology or phytomedicine paper, a blinded biochemical assay is highly valuable. Select compounds before seeing assay results using a frozen rule that balances predicted activity, uncertainty, structural diversity, availability/purity, and appropriate assay-interference filters. Include:

- positive and negative controls;
- dose–response curves and replicate design;
- compound purity/identity;
- counterscreens for aggregation, fluorescence, redox, or pan-assay interference as appropriate;
- both predicted positives and high-confidence predicted negatives;
- preregistered hit criteria.

Testing only the top predicted compounds cannot estimate specificity and invites confirmation bias.

## 10. Journal strategy

Quartiles change by database, category, and year. Recheck Scopus/SJR and Clarivate JCR at submission; the statements below concern fit, not a guarantee of rank or acceptance.

**Ranking snapshot (fact, with a source limitation).** Public SJR-derived listings available at the review cut-off place *Journal of Cheminformatics* in Q1 across its four listed 2025 categories ([CroRIS record](https://www.croris.hr/casopisi/casopis/17728)), *Journal of Ethnopharmacology* in Q1 for Drug Discovery and Pharmacology ([PubScope record](https://pubscope.org/journal/0378-8741)), *Computers in Biology and Medicine* in Q1 in its 2025 SJR listing ([Comillas record](https://www.iit.comillas.edu/publicacion/info_revista/en/730/Computers_in_Biology_and_Medicine)), and *Phytomedicine* in Q1 in the 2025 SJR listing ([JournalsBase record](https://www.journalsbase.com/journals/phytomedicine)). These are public mirrors or derived records, not the subscription-only official JCR/Scopus source lists; the team should verify the desired category in its institutional portal immediately before submission.

### 1. Journal of Cheminformatics — best fit for a rigorous open computational paper

Its scope includes cheminformatics, molecular modeling, QSAR, databases, and data mining ([scope](https://jcheminform.github.io/jcheminform-author-guidelines/aimsAndScope.html)). The journal’s October 2026 editorial explicitly prioritizes rigorous benchmarking, well-characterized datasets, data provenance, reusable code/data, and transparent AI evaluation ([Zdrazil & Martinez-Mayorga, 2026](https://doi.org/10.1186/s13321-026-01275-6)).

Best submission package: a reusable VIETHERB–ChEMBL benchmark, leakage-controlled split manifests, the hierarchical MIL method, strong classical/deep/PU baselines, and fully executable code. Wet-lab validation would help but is not essential if the benchmark/method contribution is strong.

### 2. Journal of Ethnopharmacology — best fit only with genuine ethnopharmacological interpretation and preferably experiments

The topic fits traditional-use evidence, but a generic ML screen with docking is unlikely to be enough. Follow ConSEFS for field-use provenance where relevant ([Heinrich et al., 2018](https://doi.org/10.1016/j.jep.2017.08.015)) and ConPhyMP if new extracts/plant materials are experimentally studied ([Heinrich et al., 2022](https://doi.org/10.3389/fphar.2022.953205)). The paper needs expert interpretation of Vietnamese use categories, botanical provenance, and a clear line from use report to molecular hypothesis.

### 3. Computers in Biology and Medicine — possible for a method-led biomedical study

This is viable if the model and evaluation contribution are substantial and disease relevance is explicit. It is a weaker thematic fit than Journal of Cheminformatics for a molecular-screening benchmark and weaker than Journal of Ethnopharmacology for traditional knowledge.

### 4. Phytomedicine — aspirational, experimental package required

Its scope emphasizes practical phytopharmacology, phytotherapy, extracts/isolated compounds, standardization, and pharmacological or molecular-biological studies ([official Elsevier description](https://shop.elsevier.de/phytomedicine-0944-7113.html)). A purely in-silico paper is a poor fit. Consider it only with high-quality compound or extract characterization and convincing biological validation.

**Recommendation.** Aim first at *Journal of Cheminformatics* if the main deliverable is an open benchmark/method. Aim at *Journal of Ethnopharmacology* if the team secures a pharmacognosy collaborator, validates mappings and botanical context, and performs prospective assays.

## 11. Proposed paper-level contribution statement

Use wording like this only after the experiments support it:

> We introduce a leakage-controlled benchmark linking Vietnamese medicinal-plant provenance and traditional-use annotations to experimentally measured compound-target activities. We formulate traditional use as noisy plant-level multiple-instance supervision rather than assigning plant claims to every constituent, and evaluate its incremental value under chemical and botanical cold-start settings against fingerprint, message-passing, pretrained, multi-task, and positive–unlabeled baselines. This design quantifies when ethnopharmacological knowledge improves prospective natural-product prioritization and when it induces negative transfer.

Avoid “AI validates traditional medicine.” The model generates and prioritizes molecular hypotheses; it does not establish clinical efficacy or validate a traditional claim.

## 12. Go/no-go criteria before expensive modeling

Proceed to the full paper only if the data audit establishes all of the following:

1. at least two target-relevant, expert-verifiable use groups with enough species and structure-resolved metabolites;
2. adequate curated activity data per target after organism, assay, relation, and duplicate filters;
3. a nontrivial overlap between VIETHERB chemical space and ChEMBL training support, alongside a meaningful OOD test region;
4. split construction with zero exact-molecule leakage and quantified near-neighbor leakage;
5. mapping quality high enough that expert-reviewed concept F1 and agreement are publishable;
6. an ablation showing the ethnopharmacology signal beats shuffled-label and naive-broadcast controls on a locked test set.

If item 6 fails, the project can still yield a valuable negative result or data/benchmark paper, but it should not claim that traditional-use priors improve target prediction.

## 13. Core references

### Vietnamese and traditional-medicine resources

- Nguyen-Vo T-H et al. VIETHERB: A Database for Vietnamese Herbal Species. *J Chem Inf Model*. 2019;59:1–9. [https://doi.org/10.1021/acs.jcim.8b00399](https://doi.org/10.1021/acs.jcim.8b00399)
- Trinh T et al. VietMedKG: Knowledge Graph and Benchmark for Traditional Vietnamese Medicine. *ACM TALLIP*. 2025;24(7):69. [https://doi.org/10.1145/3744740](https://doi.org/10.1145/3744740)
- Wang Y et al. A critical assessment of Traditional Chinese Medicine databases as a source for drug discovery. *Front Pharmacol*. 2024;15:1303693. [https://doi.org/10.3389/fphar.2024.1303693](https://doi.org/10.3389/fphar.2024.1303693)
- Lv Q et al. TCMBank: bridges between herbal medicines, chemical ingredients, target proteins, and diseases. *Chem Sci*. 2023;14:10684–10701. [https://doi.org/10.1039/D3SC02139D](https://doi.org/10.1039/D3SC02139D)

### Closest predictive methods

- Wang N et al. Herb Target Prediction Based on Representation Learning of Symptom related Heterogeneous Network. *Comput Struct Biotechnol J*. 2019;17:282–290. [https://doi.org/10.1016/j.csbj.2019.02.002](https://doi.org/10.1016/j.csbj.2019.02.002)
- Gan X et al. Network medicine framework reveals generic herb-symptom effectiveness of traditional Chinese medicine. *Sci Adv*. 2023;9(43):eadh0215. [https://doi.org/10.1126/sciadv.adh0215](https://doi.org/10.1126/sciadv.adh0215)
- Duan P et al. HTINet2: herb-target prediction via knowledge graph embedding and residual-like graph neural network. *Brief Bioinform*. 2024;25:bbae414. [https://doi.org/10.1093/bib/bbae414](https://doi.org/10.1093/bib/bbae414)
- Liang X et al. Herbal ingredient-target interaction prediction via multi-modal learning. *Information Sciences*. 2025;711:122115. [https://doi.org/10.1016/j.ins.2025.122115](https://doi.org/10.1016/j.ins.2025.122115)
- Cheung Y. NovelHTI: An interpretable pathway-enhanced framework for de novo target prediction of medicinal herbs. *Pharmaceuticals*. 2026;19:413. [https://doi.org/10.3390/ph19030413](https://doi.org/10.3390/ph19030413)
- Zhang J, Liu H, Guo S. SM-GAT: a safety-aware multi-task graph attention network for multi-target anti-diabetic lead discovery from natural products. *Front Mol Biosci*. 2026;13:1854162. [https://doi.org/10.3389/fmolb.2026.1854162](https://doi.org/10.3389/fmolb.2026.1854162)
- Moon C, Kim D. Prediction of drug-target interactions through multi-task learning. *Sci Rep*. 2022;12:18323. [https://doi.org/10.1038/s41598-022-23203-y](https://doi.org/10.1038/s41598-022-23203-y)
- Wang Y et al. ProDTI: Prior-Guided Positive-Unlabeled Learning for Robust Drug-Target Interaction Prediction. *Bioinformatics*. 2026;42(10):btag712. [https://doi.org/10.1093/bioinformatics/btag712](https://doi.org/10.1093/bioinformatics/btag712)

### Evaluation and reproducibility

- Yang K et al. Analyzing Learned Molecular Representations for Property Prediction. *J Chem Inf Model*. 2019;59:3370–3388. [https://doi.org/10.1021/acs.jcim.9b00237](https://doi.org/10.1021/acs.jcim.9b00237)
- Wallach I, Heifets A. Most Ligand-Based Classification Benchmarks Reward Memorization Rather than Generalization. *J Chem Inf Model*. 2018;58:916–932. [https://doi.org/10.1021/acs.jcim.7b00403](https://doi.org/10.1021/acs.jcim.7b00403)
- Sheridan RP. Time-split cross-validation as a method for estimating the goodness of prospective prediction. *J Chem Inf Model*. 2013;53:783–790. [https://doi.org/10.1021/ci400084k](https://doi.org/10.1021/ci400084k)
- Saito T, Rehmsmeier M. The Precision-Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets. *PLoS One*. 2015;10:e0118432. [https://doi.org/10.1371/journal.pone.0118432](https://doi.org/10.1371/journal.pone.0118432)
- Truchon J-F, Bayly CI. Evaluating virtual screening methods: good and bad metrics for the “early recognition” problem. *J Chem Inf Model*. 2007;47:488–508. [https://doi.org/10.1021/ci600426e](https://doi.org/10.1021/ci600426e)
- Warren GL et al. A critical assessment of docking programs and scoring functions. *J Med Chem*. 2006;49:5912–5931. [https://doi.org/10.1021/jm050362n](https://doi.org/10.1021/jm050362n)

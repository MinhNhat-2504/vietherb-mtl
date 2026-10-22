# Journal of Cheminformatics submission checklist

Verified against the official Research and general submission guidance on
2026-10-21.

## Manuscript package

- [x] Research title identifies the study scope and does not claim an empirical
  VietHerb/MIL result.
- [x] Structured abstract is below 350 words.
- [x] Abstract contains a Scientific Contribution subsection of at most three
  sentences.
- [x] Seven keywords are provided (required range: 3–10).
- [x] Full author names, one institutional address, corresponding author, email,
  and ORCIDs are present.
- [x] Main text has line and page numbering and double-line spacing.
- [x] Introduction, Methods, Results, Discussion, and Conclusions are present.
- [x] A list of abbreviations is present.
- [x] Figures are numbered in citation order and supplied as editable vector
  PDFs plus PNG previews; each is below 10 MB.
- [x] Machine-readable result tables are supplied as CSV rather than only PDF.
- [x] Additional file 1 is described and cited in the main text.
- [x] Declarations contain data availability, competing interests, funding,
  contributions, acknowledgements, ethics, and consent headings.
- [x] Generative-AI assistance is disclosed; authors retain responsibility.
- [x] Both authors confirmed the CRediT roles: Minh (conceptualization,
  methodology, software, investigation, data curation, validation,
  visualization, original draft, supervision); Linh (review and editing).
- [ ] Confirm funding, competing-interest, and final-approval wording at
  submission.
- [x] Optional graphical abstract created at 920 × 300 px on a white background;
  final JPEG is 54,960 bytes (53.67 KB), below the 150 KB limit.

## Reproducibility and archive

- [x] ChEMBL 37 archive, SQLite, extraction, dataset, run, prediction, table,
  and figure hashes are recorded.
- [x] Five fixed seeds and validation-only checkpoint/model-selection policy are
  documented.
- [x] Source code is MIT-licensed and ChEMBL source licensing is stated.
- [x] No restricted VietHerb row supports a reported conclusion.
- [x] `CITATION.cff` and `.zenodo.json` contain both authors and ORCIDs.
- [x] Copy every reported run manifest, metrics file, and prediction file into
  the release bundle.
- [x] Verify the evidence and release manifests from an LF-normalized clean
  release bundle; all 18 regenerated evidence artifacts match their reference
  hashes exactly.
- [x] Record evidence-replay wall time, Python, OS, and package versions in the
  generated evidence and environment manifests.
- [x] Enable the GitHub repository in Zenodo, create the `v0.2.1` GitHub
  release, verify archive processing, and insert version DOI
  `10.5281/zenodo.23549035` into the manuscript.
- [x] Download the published Zenodo ZIP, match its MD5, and pass release-hash,
  unit-test, Ruff, and evidence-replay checks from the extracted archive.
- [x] Pass the GitHub Actions clean-clone replay on Ubuntu for the final
  metadata-patched `main` commit (`4b2a80d`; run `39632670928`).
- [ ] Correct the published Zenodo record-level rights from MIT-only to mixed
  MIT code and CC BY-SA 3.0 ChEMBL-derived evidence.
- [ ] Optional before final DOI: re-run full model training, rather than the
  archived-evidence replay, in a clean Python 3.11 CI runner.
- [x] Confirm that all files needed to reproduce each current manuscript
  conclusion are distributable in the release bundle or accessible in public
  ChEMBL 37 under CC BY-SA 3.0. No VietHerb result is claimed.

## Submission system

- [x] Cover-letter draft explains journal fit, policy boundary, originality,
  competing interests, and author approval.
- [x] Both authors approve and sign off the cover letter (confirmed 22 October
  2026).
- [ ] Upload editable TeX/Bib sources and all figure source files; do not upload
  only the compiled PDF.
- [ ] Upload Additional file 1 and six evidence CSV tables in citation order.
- [x] Add the final Zenodo DOI as a data/software reference and in Availability
  of data and materials.
- [x] Confirm the manuscript is not published or under consideration elsewhere
  (confirmed 22 October 2026).
- [ ] Confirm APC/funding arrangements before submission.

## Scientific blockers for the later VietHerb/MIL paper

- Written VietHerb redistribution/reproducible-access terms.
- Frozen therapeutic-use mappings with two independent domain reviewers.
- Five-seed botanical cold-start MIL, shuffled-label, random-label, broadcast,
  and importance-weighted runs.
- A matched independent external dataset or prospective biochemical validation
  that passes the same locked power and disjointness gate.

These blockers do not invalidate the ChEMBL-only benchmark results, but they
prevent an empirical claim that VietHerb supervision improves target ranking.

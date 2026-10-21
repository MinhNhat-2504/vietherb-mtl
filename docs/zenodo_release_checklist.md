# Zenodo release procedure

The `v0.2.0` repository release is published on Zenodo at
https://doi.org/10.5281/zenodo.23537107. The remaining checks concern
post-publication verification and manuscript submission.

1. Review `CITATION.cff` and `.zenodo.json`. Because both exist, Zenodo uses
   `.zenodo.json` for GitHub-release metadata.
2. Assemble the release bundle from a clean clone. Include source, configs,
   `paper/main.pdf`, `paper/supplement.pdf`, `docs/evidence`, frozen run
   manifests, metrics, predictions, dataset manifests, and
   `docs/environment_manifest.json`. Do not include the proprietary/raw
   VietHerb export, the 28 GB ChEMBL SQLite database, credentials, or temporary
   Chemprop directories.
3. Run `pytest`, Ruff, `git diff --check`, dataset audits, and both LaTeX builds.
   Then run `python scripts/generate_release_manifest.py` and inspect
   `docs/release_manifest.json`.
4. Tag the exact commit as `v0.2.0` and create a GitHub release with the same
   version.
5. In Zenodo, link GitHub, enable `MinhNhat-2504/vietherb-mtl`, and archive the
   release. Wait for processing and inspect metadata and Software Heritage
   archival status.
6. Add the version DOI—not only the concept DOI—to the manuscript, supplement,
   README, and `CITATION.cff`; rebuild PDFs and create a final patch release
   if metadata changed after archiving. This was completed for
   `10.5281/zenodo.23537107`.
7. [x] Download the deposited archive and verify it in a new directory. The
   5,098,916-byte ZIP matched Zenodo MD5
   `cdddc72c70cf104f93d8c3d2b5ae65ff`; all 129 release artifacts, the complete
   unit-test suite, Ruff, and all 18 evidence artifacts passed locally.

The version DOI above resolves to the processed Zenodo archive.

The published record currently displays MIT as its record-level licence. Since
the archive mixes MIT code with ChEMBL-derived CC BY-SA 3.0 evidence, edit the
Zenodo record rights to declare both licences (or “Other (Open)” with the
file-level statement) rather than applying MIT to every file. The repository's
future-release metadata now uses `other-open` and states both terms explicitly.

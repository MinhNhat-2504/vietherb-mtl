# Zenodo release procedure

The repository is prepared for a Zenodo software archive but has not been
published. Publishing requires the corresponding GitHub/Zenodo account holder.

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
4. Tag the exact commit as `v0.1.0` and create a GitHub release with the same
   version.
5. In Zenodo, link GitHub, enable `MinhNhat-2504/vietherb-mtl`, and archive the
   release. Wait for processing and inspect metadata and Software Heritage
   archival status.
6. Add the version DOI—not only the concept DOI—to the manuscript, supplement,
   README, and `CITATION.cff`; then rebuild PDFs and create a final patch release
   if metadata changed after archiving.
7. Download the deposited archive, verify it in a new directory, and check that
   every manuscript table/figure can be traced to a hashed artifact.

No DOI should be claimed before Zenodo finishes processing the release.

# Manuscript build

`main.tex` is an English, Journal-of-Cheminformatics-oriented Research
manuscript. It reports the five-seed ChEMBL 37 chemical-OOD benchmark, temporal
and continuous sensitivities, calibration and enrichment analyses, and the
prospectively locked MIL protocol. It contains no synthetic performance values
and makes no empirical VietHerb/MIL claim. `supplement.tex` is Additional file
1 with detailed audits, per-target results, environment, and provenance.

Build with:

```powershell
cd paper
latexmk -pdf -interaction=nonstopmode main.tex
```

If `latexmk` is unavailable (or Perl is not installed), use the verified direct
sequence instead:

```powershell
cd paper
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode supplement.tex
pdflatex -interaction=nonstopmode supplement.tex
```

Before submission, confirm the author declarations, archive the exact release
on Zenodo, insert the version DOI, and reproduce the evidence package from a
clean clone. Any future VietHerb extension must populate results only from a
frozen, non-synthetic experiment whose dataset and run manifests are archived.

The BindingDB eligibility audit is reported in the manuscript and supplement;
because only one of three targets passed the locked class-count threshold, no
underpowered external performance estimate is included.

`graphical_abstract.jpg` is the optional submission-system graphical abstract.
It is a separate 920 × 300 px, white-background JPEG (53.67 KB) and is not a
numbered manuscript figure. Suggested alt text: “Three-target ChEMBL 37
benchmark comparing chemical-OOD and temporal evaluation, with classical and
graph models and a gated external-data audit.”

The compact release reproduces and verifies all publication figures and tables
without the omitted checkpoints:

```powershell
python scripts/generate_evidence_package.py `
  --archive-dir docs/manifests `
  --out artifacts/reproduced_evidence `
  --verify-reference docs/evidence
```


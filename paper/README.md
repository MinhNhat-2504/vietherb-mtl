# Manuscript build

`main.tex` is an English, Journal-of-Cheminformatics-oriented manuscript of the
registered MIL protocol and its real-data, activity-only exploratory
validation. It contains no synthetic performance values. Its claims are
deliberately bounded: the VietHerb/MIL hypothesis remains prospective until an
authorized VietHerb export is available.

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
```

Any future confirmatory extension must populate results only from a frozen,
non-synthetic experiment whose dataset and run manifests have been archived.
Confirm author identity, funding/interest declarations, journal scope, and the
current literature immediately before submission.


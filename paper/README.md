# Manuscript build

`main.tex` is an English, Journal-of-Cheminformatics-oriented working draft.
It deliberately contains labelled result placeholders; demo outputs must never
be copied into those tables.

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

Populate the Results section only from a frozen, non-synthetic experiment whose
dataset and run manifests have been archived. Re-run the literature search and
journal quartile/scope check immediately before submission.


# Confirmatory ChEMBL 37 cohort

Generated on 2026-10-21 from the official ChEMBL 37 SQLite archive. This is a
real, version-pinned activity cohort, but it is not yet the full VietHerb-MIL
experiment because authorized plant bags are unavailable.

## Source lock

- Archive SHA-256: `33c203740555f96067710cdfc1c3c55d890660e5908ec5cbf5817492c290d281`
- SQLite SHA-256: `4be13df3b68e25dcd0bff44bf094033b5aebe98f415acdc8c1cdf380e0c15142`
- Extract SHA-256: `9c77f0ab6dbf6a93c7f10aab22c4cbfd0ba696b65c6a020e9ed570048e988a8e`
- Release reported by database: `ChEMBL_37` (2026-05-01)
- Primary records: human single-protein biochemical assays, confidence >= 8,
  exact IC50/Ki measurements in nM, no validity warning or duplicate flag.

## Cohort flow

| Stage | Rows/pairs |
|---|---:|
| Candidate target records | 43,843 |
| Eligible activity records | 16,941 |
| Contradictory aggregate pairs excluded | 435 |
| Gray-zone pairs excluded | 3,353 |
| Final labelled compound-target pairs | 10,698 |
| Unique molecules | 10,686 |

The primary binary policy is active at pChEMBL >= 6, inactive at pChEMBL <= 5,
and excludes the open interval (5, 6).

## Leakage audit

- Split: 7,480 train / 1,603 validation / 1,603 test.
- Unique Murcko scaffolds: 4,417.
- Cross-split overlap: zero for molecule ID, standardized InChIKey, Murcko
  scaffold, and connected-component ID.
- Test-to-train Morgan Tanimoto: median 0.500, p95 0.673, maximum 0.698.
- Chemical-cluster threshold: 0.70 (radius 2, 2,048 bits, chirality enabled).

Machine-readable evidence is stored in `docs/manifests/chembl37_*`.

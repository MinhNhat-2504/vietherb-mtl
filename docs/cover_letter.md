# Cover letter — Journal of Cheminformatics

**Author-approved version dated 22 October 2026.**

Dear Editors,

Please consider our Research article, “Split-Dependent Transfer in Multi-Target
Bioactivity Prediction: A Leakage-Controlled ChEMBL 37 Benchmark and Locked
Plant-Bag Extension,” by Nhat Trinh Ngoc Minh and Linh Nguyen Thi My.

The manuscript addresses a recurring evaluation problem in molecular property
prediction: apparent improvement from multi-target learning can depend on how
chemical overlap, chronology, endpoint construction, and model selection are
handled. We provide a version-pinned ChEMBL 37 benchmark for human DPP4, AChE,
and COX-2, audit identity/scaffold/fingerprint-component leakage, and evaluate
five model families with five fixed seeds. Extra Trees gives the strongest
chemical-OOD ranking, Chemprop D-MPNN gives the best calibration, and the sign
of hard-sharing transfer changes between chemical-OOD classification, temporal
classification, and continuous potency. We believe this split- and
metric-dependent result is relevant to the journal's readership because it
shows why classical controls, calibration, and target-wise inference are needed
before claiming a benefit from representation or auxiliary-task complexity.

The manuscript also defines and tests the software for a plant-bag
multiple-instance learning protocol. We explicitly do not claim a VietHerb/MIL
result: that arm remains prospectively locked until a redistributable data route
and expert-audited therapeutic-use mappings exist. No restricted VietHerb row
supports the reported conclusions. This boundary is stated in the title,
abstract, results, discussion, supplement, and artifact manifests.

The code is MIT-licensed. ChEMBL-derived inputs are traceable to the public
ChEMBL 37 release, and frozen configurations, predictions, machine-readable
tables, figures, and SHA-256 manifests will be archived in Zenodo before
submission. The manuscript is not published and is not under consideration
elsewhere. The authors declare no competing interests and no external funding
for the reported computation. Both authors have approved the manuscript and
its submission.

Correspondence should be addressed to:

Linh Nguyen Thi My  
Faculty of Information Technology, Van Lang School of Technology  
Van Lang University, 69/68 Dang Thuy Tram Street, Binh Loi Trung Ward  
Ho Chi Minh City, Vietnam  
linh.ntm@vlu.edu.vn  
ORCID: 0000-0003-3990-312X

Sincerely,

Nhat Trinh Ngoc Minh, first author  
Linh Nguyen Thi My, corresponding author

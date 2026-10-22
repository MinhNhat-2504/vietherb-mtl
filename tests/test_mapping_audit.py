from __future__ import annotations

import pandas as pd

from scripts.audit_therapeutic_mapping import audit


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "raw_use_normalized": ["diabetes", "memory", "pain", "diabetes"],
            "term_id": ["D1", "N1", "I1", "D1"],
            "term_label": ["diabetes", "memory", "pain", "diabetes"],
            "ontology": ["project"] * 4,
            "auxiliary_task": [
                "ethno_diabetes",
                "ethno_neuro",
                "ethno_inflammation",
                "ethno_diabetes",
            ],
            "mapping_method": ["manual"] * 4,
            "mapping_confidence": [0.9, 0.8, 0.7, 0.9],
            "reviewer_1": ["accept"] * 4,
            "reviewer_2": ["accept"] * 4,
            "adjudicated": ["accept"] * 4,
            "notes": [""] * 4,
        }
    )


def test_empty_table_is_explicitly_pending() -> None:
    report = audit(_frame().iloc[0:0], sample_size=300, seed=20261020, bootstrap_replicates=50)
    assert report["status"] == "pending_authorized_export"


def test_complete_small_table_reports_agreement() -> None:
    report = audit(_frame(), sample_size=4, seed=20261020, bootstrap_replicates=50)
    assert report["status"] == "complete"
    assert report["agreement"]["complete_reviewer_pairs"] == 4
    assert report["agreement"]["exact_agreement"] == 1.0

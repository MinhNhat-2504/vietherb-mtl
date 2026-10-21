import pytest

from vietherb_mtl.selection import select_validation_configuration


def test_validation_selection_averages_seeds_and_is_order_invariant():
    records = [
        {"weight": 0.1, "seed": 1, "validation_macro_pr_auc": 0.70},
        {"weight": 0.1, "seed": 2, "validation_macro_pr_auc": 0.80},
        {"weight": 0.3, "seed": 1, "validation_macro_pr_auc": 0.78},
        {"weight": 0.3, "seed": 2, "validation_macro_pr_auc": 0.76},
    ]
    selected = select_validation_configuration(records, parameter_names=["weight"])
    reversed_selected = select_validation_configuration(
        list(reversed(records)), parameter_names=["weight"]
    )
    assert selected == reversed_selected
    assert selected["weight"] == 0.3
    assert selected["mean_validation_score"] == pytest.approx(0.77)


def test_validation_selection_rejects_test_metric():
    with pytest.raises(ValueError, match="test metrics"):
        select_validation_configuration(
            [{"weight": 0.1, "test_pr_auc": 0.9}],
            parameter_names=["weight"],
            score_name="test_pr_auc",
        )

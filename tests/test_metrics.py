import math

import pytest

from vietherb_mtl.metrics import (
    bedroc_score,
    benjamini_hochberg,
    ef1_score,
    ef5_score,
    enrichment_factor,
    expected_calibration_error,
    mean_absolute_error,
    pr_auc_score,
    precision_recall_at_fraction,
    reliability_bins,
    root_mean_squared_error,
    spearman_correlation,
)


def test_perfect_ranking_metrics():
    labels = [1, 1, 0, 0]
    scores = [0.9, 0.8, 0.2, 0.1]
    assert pr_auc_score(labels, scores) == pytest.approx(1.0)
    assert bedroc_score(labels, scores) == pytest.approx(1.0)
    assert enrichment_factor(labels, scores, fraction=0.5) == pytest.approx(2.0)


def test_worst_bedroc_is_zero_and_ties_are_order_invariant():
    assert bedroc_score([0, 0, 1, 1], [0.9, 0.8, 0.2, 0.1]) == pytest.approx(0.0)
    a = pr_auc_score([1, 0, 1], [0.5, 0.5, 0.1])
    b = pr_auc_score([0, 1, 1], [0.5, 0.5, 0.1])
    assert a == pytest.approx(b)


def test_nan_pairs_are_ignored_and_ef1_alias_works():
    labels = [1, 0, 1]
    scores = [1.0, math.nan, 0.0]
    assert pr_auc_score(labels, scores) == 1.0
    assert ef1_score(labels, scores) == enrichment_factor(labels, scores, fraction=0.01)


def test_budget_metrics_and_ef5():
    labels = [1, 1, 0, 0]
    scores = [0.9, 0.8, 0.2, 0.1]
    precision, recall = precision_recall_at_fraction(labels, scores, fraction=0.5)
    assert precision == pytest.approx(1.0)
    assert recall == pytest.approx(1.0)
    assert ef5_score(labels, scores) == enrichment_factor(labels, scores, fraction=0.05)


def test_expected_calibration_error():
    assert expected_calibration_error([0, 1], [0.0, 1.0]) == pytest.approx(0.0)
    assert expected_calibration_error([0, 1], [0.5, 0.5]) == pytest.approx(0.0)
    with pytest.raises(ValueError, match="probabilities"):
        expected_calibration_error([0, 1], [-0.1, 1.1])


def test_reliability_and_continuous_metrics():
    bins = reliability_bins([0, 1, 1], [0.1, 0.8, 0.9], n_bins=2)
    assert bins[0]["count"] == 1
    assert bins[1]["observed_fraction"] == pytest.approx(1.0)
    assert mean_absolute_error([1, 2], [2, 2]) == pytest.approx(0.5)
    assert root_mean_squared_error([1, 2], [2, 2]) == pytest.approx(math.sqrt(0.5))
    assert spearman_correlation([1, 2, 3], [10, 20, 30]) == pytest.approx(1.0)


def test_benjamini_hochberg_preserves_input_order():
    adjusted = benjamini_hochberg([0.01, 0.04, 0.03])
    assert adjusted == pytest.approx([0.03, 0.04, 0.04])

"""Dependency-free ranking metrics for virtual-screening evaluation."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np


def _validated_pairs(
    y_true: Sequence[int | float], y_score: Sequence[int | float]
) -> list[tuple[int, float]]:
    if len(y_true) != len(y_score):
        raise ValueError("y_true and y_score must have the same length")
    pairs: list[tuple[int, float]] = []
    for label, score in zip(y_true, y_score, strict=True):
        numeric_label = float(label)
        numeric_score = float(score)
        if not math.isfinite(numeric_label) or not math.isfinite(numeric_score):
            continue
        if numeric_label not in (0.0, 1.0):
            raise ValueError("labels must be binary (0 or 1)")
        pairs.append((int(numeric_label), numeric_score))
    if not pairs:
        raise ValueError("no finite label/score pairs")
    return pairs


def pr_auc_score(y_true: Sequence[int | float], y_score: Sequence[int | float]) -> float:
    """Average precision, a step-wise area under the precision-recall curve.

    Tied scores are processed as a block, so the result does not depend on row
    ordering. Missing pairs (NaN/inf) are ignored.
    """

    pairs = _validated_pairs(y_true, y_score)
    positives = sum(label for label, _ in pairs)
    if positives == 0:
        raise ValueError("PR-AUC is undefined without a positive label")
    pairs.sort(key=lambda item: item[1], reverse=True)
    true_positives = 0
    seen = 0
    area = 0.0
    previous_recall = 0.0
    cursor = 0
    while cursor < len(pairs):
        score = pairs[cursor][1]
        end = cursor
        block_positives = 0
        while end < len(pairs) and pairs[end][1] == score:
            block_positives += pairs[end][0]
            end += 1
        true_positives += block_positives
        seen = end
        recall = true_positives / positives
        precision = true_positives / seen
        area += (recall - previous_recall) * precision
        previous_recall = recall
        cursor = end
    return area


def _average_ranks_descending(pairs: list[tuple[int, float]]) -> list[tuple[int, float]]:
    pairs = sorted(pairs, key=lambda item: item[1], reverse=True)
    ranked: list[tuple[int, float]] = []
    cursor = 0
    while cursor < len(pairs):
        end = cursor + 1
        while end < len(pairs) and pairs[end][1] == pairs[cursor][1]:
            end += 1
        average_rank = ((cursor + 1) + end) / 2.0  # one-based ranks
        ranked.extend((label, average_rank) for label, _ in pairs[cursor:end])
        cursor = end
    return ranked


def bedroc_score(
    y_true: Sequence[int | float],
    y_score: Sequence[int | float],
    *,
    alpha: float = 20.0,
) -> float:
    """Boltzmann-enhanced discrimination of ROC, normalized to [0, 1].

    Larger ``alpha`` emphasizes earlier ranks. Average ranks make ties invariant
    to input order. The score is undefined unless both classes are present.
    """

    if alpha <= 0 or not math.isfinite(alpha):
        raise ValueError("alpha must be finite and positive")
    pairs = _validated_pairs(y_true, y_score)
    total = len(pairs)
    positives = sum(label for label, _ in pairs)
    if positives == 0 or positives == total:
        raise ValueError("BEDROC requires both positive and negative labels")
    ranks = [rank for label, rank in _average_ranks_descending(pairs) if label]
    observed = sum(math.exp(-alpha * rank / total) for rank in ranks)
    best = sum(math.exp(-alpha * rank / total) for rank in range(1, positives + 1))
    worst = sum(math.exp(-alpha * rank / total) for rank in range(total - positives + 1, total + 1))
    return min(1.0, max(0.0, (observed - worst) / (best - worst)))


def enrichment_factor(
    y_true: Sequence[int | float],
    y_score: Sequence[int | float],
    *,
    fraction: float = 0.01,
) -> float:
    """Enrichment factor in the top fraction (EF1% by default).

    The cutoff contains at least one item (``ceil(N * fraction)``). Ties at the
    boundary use the expected positive count from the tied block, avoiding
    dependence on the original row order.
    """

    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")
    pairs = _validated_pairs(y_true, y_score)
    positives = sum(label for label, _ in pairs)
    if positives == 0:
        raise ValueError("enrichment factor is undefined without positives")
    pairs.sort(key=lambda item: item[1], reverse=True)
    cutoff = max(1, math.ceil(len(pairs) * fraction))
    threshold = pairs[cutoff - 1][1]
    above = [label for label, score in pairs if score > threshold]
    tied = [label for label, score in pairs if score == threshold]
    slots = cutoff - len(above)
    expected_top_positives = sum(above) + slots * (sum(tied) / len(tied))
    return (expected_top_positives / cutoff) / (positives / len(pairs))


def ef1_score(y_true: Sequence[int | float], y_score: Sequence[int | float]) -> float:
    """Convenience alias for enrichment factor at 1%."""

    return enrichment_factor(y_true, y_score, fraction=0.01)


def ef5_score(y_true: Sequence[int | float], y_score: Sequence[int | float]) -> float:
    """Convenience alias for enrichment factor at 5%."""

    return enrichment_factor(y_true, y_score, fraction=0.05)


def precision_recall_at_fraction(
    y_true: Sequence[int | float],
    y_score: Sequence[int | float],
    *,
    fraction: float = 0.01,
) -> tuple[float, float]:
    """Expected precision and recall at a fixed screening budget.

    Boundary ties contribute their expected positive count, matching the tie
    policy used by :func:`enrichment_factor`.
    """

    if not 0 < fraction <= 1:
        raise ValueError("fraction must be in (0, 1]")
    pairs = _validated_pairs(y_true, y_score)
    positives = sum(label for label, _ in pairs)
    if positives == 0:
        raise ValueError("precision/recall is undefined without positives")
    pairs.sort(key=lambda item: item[1], reverse=True)
    cutoff = max(1, math.ceil(len(pairs) * fraction))
    threshold = pairs[cutoff - 1][1]
    above = [label for label, score in pairs if score > threshold]
    tied = [label for label, score in pairs if score == threshold]
    expected_true_positives = sum(above) + (cutoff - len(above)) * (sum(tied) / len(tied))
    return expected_true_positives / cutoff, expected_true_positives / positives


def expected_calibration_error(
    y_true: Sequence[int | float],
    y_score: Sequence[int | float],
    *,
    n_bins: int = 10,
) -> float:
    """Equal-width expected calibration error for probability predictions."""

    if n_bins < 2:
        raise ValueError("n_bins must be at least 2")
    pairs = _validated_pairs(y_true, y_score)
    if any(score < 0 or score > 1 for _, score in pairs):
        raise ValueError("calibration scores must be probabilities in [0, 1]")
    total = len(pairs)
    error = 0.0
    for bin_index in range(n_bins):
        lower = bin_index / n_bins
        upper = (bin_index + 1) / n_bins
        members = [
            (label, score)
            for label, score in pairs
            if lower <= score < upper or (bin_index == n_bins - 1 and score == 1.0)
        ]
        if not members:
            continue
        accuracy = sum(label for label, _ in members) / len(members)
        confidence = sum(score for _, score in members) / len(members)
        error += len(members) / total * abs(accuracy - confidence)
    return error


def reliability_bins(
    y_true: Sequence[int | float],
    y_score: Sequence[int | float],
    *,
    n_bins: int = 10,
) -> list[dict[str, float | int]]:
    """Return equal-width reliability-diagram bins, including empty bins."""

    if n_bins < 2:
        raise ValueError("n_bins must be at least 2")
    pairs = _validated_pairs(y_true, y_score)
    if any(score < 0 or score > 1 for _, score in pairs):
        raise ValueError("calibration scores must be probabilities in [0, 1]")
    result: list[dict[str, float | int]] = []
    for bin_index in range(n_bins):
        lower = bin_index / n_bins
        upper = (bin_index + 1) / n_bins
        members = [
            (label, score)
            for label, score in pairs
            if lower <= score < upper or (bin_index == n_bins - 1 and score == 1.0)
        ]
        result.append(
            {
                "bin": bin_index,
                "lower": lower,
                "upper": upper,
                "count": len(members),
                "mean_probability": (
                    math.nan if not members else sum(score for _, score in members) / len(members)
                ),
                "observed_fraction": (
                    math.nan if not members else sum(label for label, _ in members) / len(members)
                ),
            }
        )
    return result


def mean_absolute_error(
    y_true: Sequence[int | float], y_score: Sequence[int | float]
) -> float:
    """MAE after dropping non-finite pairs."""

    pairs = _finite_numeric_pairs(y_true, y_score)
    return float(np.mean([abs(truth - score) for truth, score in pairs]))


def root_mean_squared_error(
    y_true: Sequence[int | float], y_score: Sequence[int | float]
) -> float:
    """RMSE after dropping non-finite pairs."""

    pairs = _finite_numeric_pairs(y_true, y_score)
    return float(np.sqrt(np.mean([(truth - score) ** 2 for truth, score in pairs])))


def spearman_correlation(
    y_true: Sequence[int | float], y_score: Sequence[int | float]
) -> float:
    """Spearman correlation with average ranks for ties."""

    pairs = _finite_numeric_pairs(y_true, y_score)
    if len(pairs) < 2:
        raise ValueError("Spearman correlation requires at least two pairs")
    truth = np.asarray([item[0] for item in pairs], dtype=float)
    score = np.asarray([item[1] for item in pairs], dtype=float)
    truth_rank = _average_rank(truth)
    score_rank = _average_rank(score)
    if np.std(truth_rank) == 0 or np.std(score_rank) == 0:
        raise ValueError("Spearman correlation is undefined for a constant input")
    return float(np.corrcoef(truth_rank, score_rank)[0, 1])


def benjamini_hochberg(p_values: Sequence[int | float]) -> list[float]:
    """Benjamini--Hochberg adjusted p-values in original input order."""

    values = np.asarray(p_values, dtype=float)
    if values.ndim != 1 or len(values) == 0:
        raise ValueError("p_values must be a non-empty one-dimensional sequence")
    if np.any(~np.isfinite(values)) or np.any((values < 0) | (values > 1)):
        raise ValueError("p-values must be finite and in [0, 1]")
    order = np.argsort(values)
    ranked = values[order]
    adjusted_ranked = ranked * len(values) / np.arange(1, len(values) + 1)
    adjusted_ranked = np.minimum.accumulate(adjusted_ranked[::-1])[::-1]
    adjusted = np.empty_like(adjusted_ranked)
    adjusted[order] = np.minimum(adjusted_ranked, 1.0)
    return adjusted.tolist()


def _finite_numeric_pairs(
    y_true: Sequence[int | float], y_score: Sequence[int | float]
) -> list[tuple[float, float]]:
    if len(y_true) != len(y_score):
        raise ValueError("y_true and y_score must have the same length")
    pairs = [
        (float(truth), float(score))
        for truth, score in zip(y_true, y_score, strict=True)
        if math.isfinite(float(truth)) and math.isfinite(float(score))
    ]
    if not pairs:
        raise ValueError("no finite truth/score pairs")
    return pairs


def _average_rank(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    cursor = 0
    while cursor < len(values):
        end = cursor + 1
        while end < len(values) and values[order[end]] == values[order[cursor]]:
            end += 1
        ranks[order[cursor:end]] = ((cursor + 1) + end) / 2.0
        cursor = end
    return ranks

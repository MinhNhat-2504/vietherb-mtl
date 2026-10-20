"""Dependency-free ranking metrics for virtual-screening evaluation."""

from __future__ import annotations

import math
from collections.abc import Sequence


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

"""Masked binary losses for sparsely-labelled multi-task data."""

from __future__ import annotations

import math
from collections.abc import Mapping

try:
    import torch
    from torch import Tensor
    from torch.nn import functional as F
except ImportError:  # pragma: no cover
    torch = None
    Tensor = object  # type: ignore[assignment,misc]
    F = None


def _require_torch() -> None:
    if torch is None:
        raise ImportError("masked BCE losses require PyTorch; install torch first")


def masked_bce_with_logits(
    logits: Tensor,
    targets: Tensor,
    mask: Tensor | None = None,
    *,
    pos_weight: Tensor | None = None,
    reduction: str = "mean",
) -> Tensor:
    """BCE-with-logits ignoring missing (NaN) or explicitly masked labels.

    A differentiable scalar zero is returned for an all-missing mean/sum batch,
    which makes sparse mini-batches safe during training.
    """

    _require_torch()
    if logits.shape != targets.shape:
        raise ValueError("logits and targets must have identical shapes")
    if reduction not in {"none", "mean", "sum"}:
        raise ValueError("reduction must be one of: none, mean, sum")

    valid = torch.isfinite(targets)
    if mask is not None:
        if mask.shape != targets.shape:
            raise ValueError("mask and targets must have identical shapes")
        valid = valid & mask.to(dtype=torch.bool)
    clean_targets = torch.where(valid, targets, torch.zeros_like(targets))
    losses = F.binary_cross_entropy_with_logits(
        logits, clean_targets, pos_weight=pos_weight, reduction="none"
    )
    losses = torch.where(valid, losses, torch.zeros_like(losses))
    if reduction == "none":
        return losses
    total = losses.sum()
    if reduction == "sum":
        return total
    return total / valid.sum().clamp_min(1).to(dtype=total.dtype)


def nnpu_loss(
    logits: Tensor,
    targets: Tensor,
    prior: float,
    beta: float = 0.0,
    gamma: float = 1.0,
) -> Tensor:
    """Non-negative positive-unlabeled logistic loss (Kiryo et al., 2017).

    ``targets == 1`` means an observed positive and ``targets == 0`` means
    *unlabeled*, not a confirmed negative. ``prior`` is the estimated positive
    class prevalence :math:`P(y=1)` for this auxiliary label and must be in
    ``(0, 1)``. In a multi-label experiment, call this function independently
    for each auxiliary label using its own class prior.

    When the empirical negative risk drops below ``-beta``, the returned
    ``-gamma * negative_risk`` supplies the differentiable gradient correction
    from nnPU. Both positive and unlabeled examples are required in the batch;
    use stratified batches or accumulate examples when labels are very sparse.
    """

    _require_torch()
    if logits.shape != targets.shape:
        raise ValueError("logits and targets must have identical shapes")
    if logits.numel() == 0:
        raise ValueError("nnPU requires a non-empty batch")
    if not logits.is_floating_point():
        raise TypeError("logits must be a floating-point tensor")
    if not bool(torch.isfinite(logits).all()):
        raise ValueError("logits must be finite")
    if not bool(torch.isfinite(targets).all()):
        raise ValueError("targets must be finite; encode unlabeled examples as 0")
    if not bool(((targets == 0) | (targets == 1)).all()):
        raise ValueError("nnPU targets must be 1 (positive) or 0 (unlabeled)")
    try:
        prior_value = float(prior)
        beta_value = float(beta)
        gamma_value = float(gamma)
    except (TypeError, ValueError) as error:
        raise TypeError("prior, beta, and gamma must be real scalars") from error
    if not 0.0 < prior_value < 1.0:
        raise ValueError("prior must be in the open interval (0, 1)")
    if not math.isfinite(beta_value) or beta_value < 0.0:
        raise ValueError("beta must be finite and non-negative")
    if not math.isfinite(gamma_value) or gamma_value < 0.0:
        raise ValueError("gamma must be finite and non-negative")

    positive = targets == 1
    unlabeled = targets == 0
    if not bool(positive.any()):
        raise ValueError("nnPU requires at least one observed positive")
    if not bool(unlabeled.any()):
        raise ValueError("nnPU requires at least one unlabeled example")

    # Logistic surrogate: softplus(-g) for y=+1, softplus(g) for y=-1.
    positive_risk = prior_value * F.softplus(-logits[positive]).mean()
    negative_risk = F.softplus(logits[unlabeled]).mean()
    negative_risk = negative_risk - prior_value * F.softplus(logits[positive]).mean()

    unbiased_risk = positive_risk + negative_risk
    corrected_risk = -gamma_value * negative_risk
    return torch.where(negative_risk < -beta_value, corrected_risk, unbiased_risk)


def multitask_masked_bce(
    logits: Mapping[str, Tensor],
    targets: Mapping[str, Tensor],
    masks: Mapping[str, Tensor] | None = None,
    *,
    task_weights: Mapping[str, float] | None = None,
) -> tuple[Tensor, dict[str, Tensor]]:
    """Compute a weighted mean of per-task masked BCE losses.

    Returns ``(total_loss, per_task_losses)`` for transparent logging. Tasks in
    ``targets`` must exactly match those in ``logits`` to catch silent data bugs.
    """

    _require_torch()
    if set(logits) != set(targets):
        raise ValueError("logit and target task names must match exactly")
    if not logits:
        raise ValueError("at least one task is required")
    unknown_masks = set(masks or {}) - set(logits)
    if unknown_masks:
        raise ValueError(f"masks contain unknown tasks: {sorted(unknown_masks)}")

    losses: dict[str, Tensor] = {}
    weighted = None
    weight_sum = 0.0
    for task, task_logits in logits.items():
        weight = float((task_weights or {}).get(task, 1.0))
        if weight < 0:
            raise ValueError("task weights cannot be negative")
        loss = masked_bce_with_logits(
            task_logits,
            targets[task],
            None if masks is None else masks.get(task),
        )
        losses[task] = loss
        if weight:
            weighted = loss * weight if weighted is None else weighted + loss * weight
            weight_sum += weight
    if weighted is None:
        # Keep the zero connected to the graph even when every weight is zero.
        first = next(iter(logits.values()))
        total = first.sum() * 0.0
    else:
        total = weighted / weight_sum
    return total, losses

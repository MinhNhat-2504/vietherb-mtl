"""Herb-level multiple-instance learning without broadcasting bag labels."""

from __future__ import annotations

try:
    import torch
    from torch import Tensor, nn
except ImportError:  # pragma: no cover - exercised in dependency-light installs
    torch = None
    Tensor = object  # type: ignore[assignment,misc]
    nn = None

from .losses import masked_bce_with_logits, nnpu_loss


def _validate_bag_tensors(
    instance_embeddings: Tensor, bag_index: Tensor, embedding_dim: int
) -> int:
    """Validate a packed bag representation and return its number of bags."""

    if instance_embeddings.ndim != 2:
        raise ValueError("instance_embeddings must have shape [instances, embedding_dim]")
    if instance_embeddings.shape[1] != embedding_dim:
        raise ValueError(
            f"expected embedding dimension {embedding_dim}, got {instance_embeddings.shape[1]}"
        )
    if instance_embeddings.shape[0] == 0:
        raise ValueError("MIL aggregation requires at least one instance")
    if not instance_embeddings.is_floating_point():
        raise TypeError("instance_embeddings must be floating point")
    if not bool(torch.isfinite(instance_embeddings).all()):
        raise ValueError("instance_embeddings must be finite")
    if bag_index.ndim != 1:
        raise ValueError("bag_index must be one-dimensional")
    if bag_index.shape[0] != instance_embeddings.shape[0]:
        raise ValueError("bag_index must contain one entry per instance")
    if bag_index.device != instance_embeddings.device:
        raise ValueError("bag_index and instance_embeddings must be on the same device")
    integer_dtypes = {
        torch.int8,
        torch.int16,
        torch.int32,
        torch.int64,
        torch.uint8,
    }
    if bag_index.dtype not in integer_dtypes:
        raise TypeError("bag_index must use an integer dtype")
    if bool((bag_index < 0).any()):
        raise ValueError("bag_index cannot contain negative IDs")

    unique_bags = torch.unique(bag_index, sorted=True)
    expected = torch.arange(unique_bags.numel(), device=bag_index.device, dtype=bag_index.dtype)
    if not bool(torch.equal(unique_bags, expected)):
        raise ValueError("bag_index IDs must be contiguous from 0; a gap denotes an empty bag")
    return int(unique_bags.numel())


if nn is not None:

    class AttentionMILAggregator(nn.Module):
        """Ilse-style attention pooling from compound instances to herb bags.

        Input is a packed tensor of instance embeddings and a parallel bag index.
        The result is ``(bag_logits, attention_weights)`` with shapes
        ``[n_bags, output_dim]`` and ``[n_instances]``. Attention is shared across
        output tasks and sums to one independently inside every bag.
        """

        def __init__(
            self,
            embedding_dim: int,
            output_dim: int = 1,
            attention_dim: int = 128,
            *,
            gated: bool = True,
        ) -> None:
            super().__init__()
            if embedding_dim <= 0:
                raise ValueError("embedding_dim must be positive")
            if output_dim <= 0:
                raise ValueError("output_dim must be positive")
            if attention_dim <= 0:
                raise ValueError("attention_dim must be positive")
            self.embedding_dim = embedding_dim
            self.output_dim = output_dim
            self.gated = gated
            self.attention_v = nn.Linear(embedding_dim, attention_dim)
            self.attention_u = nn.Linear(embedding_dim, attention_dim) if gated else None
            self.attention_w = nn.Linear(attention_dim, 1, bias=False)
            self.classifier = nn.Linear(embedding_dim, output_dim)

        def forward(self, instance_embeddings: Tensor, bag_index: Tensor) -> tuple[Tensor, Tensor]:
            n_bags = _validate_bag_tensors(instance_embeddings, bag_index, self.embedding_dim)
            attention_hidden = torch.tanh(self.attention_v(instance_embeddings))
            if self.attention_u is not None:
                attention_hidden = attention_hidden * torch.sigmoid(
                    self.attention_u(instance_embeddings)
                )
            attention_scores = self.attention_w(attention_hidden).squeeze(-1)

            # A small explicit loop keeps the implementation dependency-free;
            # the expensive transformations above remain fully vectorized.
            attention_weights = torch.zeros_like(attention_scores)
            bag_embeddings: list[Tensor] = []
            for bag_id in range(n_bags):
                positions = torch.nonzero(bag_index == bag_id, as_tuple=False).squeeze(1)
                local_weights = torch.softmax(attention_scores[positions], dim=0)
                attention_weights = attention_weights.scatter(0, positions, local_weights)
                bag_embeddings.append(
                    torch.sum(
                        local_weights.unsqueeze(-1) * instance_embeddings[positions],
                        dim=0,
                    )
                )
            packed_bags = torch.stack(bag_embeddings, dim=0)
            return self.classifier(packed_bags), attention_weights

else:

    class AttentionMILAggregator:  # pragma: no cover - depends on environment
        """Import-safe placeholder explaining the optional PyTorch dependency."""

        def __init__(
            self,
            embedding_dim: int,
            output_dim: int = 1,
            attention_dim: int = 128,
            *,
            gated: bool = True,
        ) -> None:
            del embedding_dim, output_dim, attention_dim, gated
            raise ImportError("AttentionMILAggregator requires PyTorch")


def bag_masked_bce_with_logits(
    bag_logits: Tensor,
    bag_targets: Tensor,
    mask: Tensor | None = None,
    *,
    pos_weight: Tensor | None = None,
    reduction: str = "mean",
) -> Tensor:
    """Masked BCE on bag predictions; labels are never expanded to instances."""

    if bag_logits.ndim not in (1, 2):
        raise ValueError("bag logits/targets must have shape [bags] or [bags, tasks]")
    return masked_bce_with_logits(
        bag_logits,
        bag_targets,
        mask,
        pos_weight=pos_weight,
        reduction=reduction,
    )


def bag_nnpu_loss(
    bag_logits: Tensor,
    bag_targets: Tensor,
    prior: float,
    beta: float = 0.0,
    gamma: float = 1.0,
) -> Tensor:
    """nnPU loss for one herb-level label (1=observed use, 0=unlabeled)."""

    if bag_logits.ndim not in (1, 2):
        raise ValueError("bag logits/targets must have shape [bags] or [bags, 1]")
    if bag_logits.ndim == 2 and bag_logits.shape[1] != 1:
        raise ValueError("bag_nnpu_loss handles one label; call it once per label")
    return nnpu_loss(bag_logits, bag_targets, prior, beta=beta, gamma=gamma)

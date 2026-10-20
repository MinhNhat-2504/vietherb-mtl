import pytest

torch = pytest.importorskip("torch")

from vietherb_mtl.mil import (  # noqa: E402
    AttentionMILAggregator,
    bag_masked_bce_with_logits,
    bag_nnpu_loss,
)


def _aggregator():
    torch.manual_seed(3)
    return AttentionMILAggregator(embedding_dim=5, output_dim=3, attention_dim=4, gated=True)


def test_attention_mil_shapes_and_weights_sum_within_each_bag():
    model = _aggregator()
    embeddings = torch.randn(6, 5)
    bag_index = torch.tensor([0, 0, 1, 2, 2, 2])
    logits, weights = model(embeddings, bag_index)
    assert logits.shape == (3, 3)
    assert weights.shape == (6,)
    for bag_id in range(3):
        assert weights[bag_index == bag_id].sum().item() == pytest.approx(1.0)


def test_attention_mil_is_permutation_invariant_inside_bags():
    model = _aggregator()
    embeddings = torch.randn(6, 5)
    bag_index = torch.tensor([0, 0, 0, 1, 1, 1])
    logits, weights = model(embeddings, bag_index)
    permutation = torch.tensor([2, 0, 1, 5, 3, 4])
    permuted_logits, permuted_weights = model(embeddings[permutation], bag_index[permutation])
    assert torch.allclose(logits, permuted_logits, atol=1e-6)
    assert torch.allclose(weights[permutation], permuted_weights, atol=1e-6)


def test_attention_mil_backpropagates_to_every_instance():
    model = _aggregator()
    embeddings = torch.randn(5, 5, requires_grad=True)
    logits, weights = model(embeddings, torch.tensor([0, 0, 1, 1, 1]))
    (logits.square().mean() + weights.square().mean()).backward()
    assert embeddings.grad is not None
    assert embeddings.grad.shape == embeddings.shape
    assert torch.isfinite(embeddings.grad).all()
    assert embeddings.grad.abs().sum().item() > 0


@pytest.mark.parametrize(
    "bag_index, message",
    [
        (torch.tensor([0, 2]), "contiguous"),
        (torch.tensor([0, -1]), "negative"),
        (torch.tensor([0.0, 0.0]), "integer dtype"),
        (torch.tensor([[0, 0]]), "one-dimensional"),
    ],
)
def test_attention_mil_rejects_invalid_bag_index(bag_index, message):
    model = _aggregator()
    with pytest.raises((ValueError, TypeError), match=message):
        model(torch.randn(2, 5), bag_index)


def test_attention_mil_rejects_empty_instances():
    with pytest.raises(ValueError, match="at least one instance"):
        _aggregator()(torch.empty(0, 5), torch.empty(0, dtype=torch.long))


def test_bag_level_loss_wrappers_operate_without_label_broadcasting():
    logits = torch.tensor([0.0, 1.0, -1.0], requires_grad=True)
    masked_loss = bag_masked_bce_with_logits(logits, torch.tensor([1.0, float("nan"), 0.0]))
    pu_loss = bag_nnpu_loss(logits, torch.tensor([1.0, 0.0, 0.0]), prior=0.2)
    total = masked_loss + pu_loss
    total.backward()
    assert total.ndim == 0
    assert logits.grad is not None

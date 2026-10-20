import pytest

torch = pytest.importorskip("torch")

from vietherb_mtl.config import ModelConfig  # noqa: E402
from vietherb_mtl.losses import (  # noqa: E402
    masked_bce_with_logits,
    multitask_masked_bce,
    nnpu_loss,
)
from vietherb_mtl.model import MultiTaskMLP  # noqa: E402


def test_multitask_model_shapes_and_task_names():
    config = ModelConfig(
        input_dim=16,
        hidden_dims=(8,),
        primary_tasks=("target_a", "target_b"),
        auxiliary_tasks=("diabetes", "neuro", "inflammation"),
        dropout=0.0,
    )
    model = MultiTaskMLP(config)
    features = torch.zeros(4, 16)
    assert model.encode(features).shape == (4, 8)
    outputs = model(features)
    assert set(outputs) == {
        "target_a",
        "target_b",
        "diabetes",
        "neuro",
        "inflammation",
    }
    assert all(value.shape == (4,) for value in outputs.values())


def test_legacy_single_auxiliary_task_alias():
    config = ModelConfig(
        input_dim=8,
        hidden_dims=(4,),
        auxiliary_task="ethnomedical",
        dropout=0.0,
    )
    assert config.auxiliary_tasks == ("ethnomedical",)
    assert set(MultiTaskMLP(config)(torch.zeros(2, 8))) == {"activity", "ethnomedical"}


def test_masked_bce_ignores_nan_and_preserves_gradient():
    logits = torch.tensor([0.0, 0.0, 3.0], requires_grad=True)
    targets = torch.tensor([1.0, float("nan"), 0.0])
    loss = masked_bce_with_logits(logits, targets)
    expected = (
        torch.nn.functional.binary_cross_entropy_with_logits(logits[0], targets[0])
        + torch.nn.functional.binary_cross_entropy_with_logits(logits[2], targets[2])
    ) / 2
    assert loss.item() == pytest.approx(expected.detach().item())
    loss.backward()
    assert logits.grad[1].item() == 0.0


def test_multitask_loss_returns_logging_breakdown():
    logits = {"primary": torch.zeros(2), "ethnomedical": torch.zeros(2)}
    targets = {
        "primary": torch.tensor([1.0, 0.0]),
        "ethnomedical": torch.tensor([1.0, float("nan")]),
    }
    total, per_task = multitask_masked_bce(
        logits, targets, task_weights={"primary": 1.0, "ethnomedical": 0.25}
    )
    assert total.item() == pytest.approx(0.69314718056)
    assert set(per_task) == set(logits)


def test_nnpu_matches_unbiased_risk_when_negative_risk_is_nonnegative():
    logits = torch.zeros(4, requires_grad=True)
    targets = torch.tensor([1.0, 1.0, 0.0, 0.0])
    loss = nnpu_loss(logits, targets, prior=0.25)
    # At zero logits both class-conditional logistic losses equal log(2), and
    # the prior-weighted terms cancel to yield log(2).
    assert loss.item() == pytest.approx(0.69314718056)
    loss.backward()
    assert logits.grad is not None
    assert torch.isfinite(logits.grad).all()


def test_nnpu_correction_branch_is_differentiable():
    # Strongly positive logits for all examples make the estimated negative
    # risk negative for a sufficiently large class prior.
    logits = torch.tensor([10.0, 1.0], requires_grad=True)
    targets = torch.tensor([1.0, 0.0])
    loss = nnpu_loss(logits, targets, prior=0.9, beta=0.0, gamma=1.0)
    positive_negative_loss = torch.nn.functional.softplus(logits[0])
    unlabeled_negative_loss = torch.nn.functional.softplus(logits[1])
    negative_risk = unlabeled_negative_loss - 0.9 * positive_negative_loss
    assert negative_risk.item() < 0
    assert loss.item() == pytest.approx((-negative_risk).detach().item())
    loss.backward()
    assert logits.grad is not None
    assert logits.grad.abs().sum().item() > 0


@pytest.mark.parametrize("prior", [0.0, 1.0, -0.1, 1.1])
def test_nnpu_rejects_invalid_prior(prior):
    with pytest.raises(ValueError, match="prior"):
        nnpu_loss(torch.zeros(2), torch.tensor([1.0, 0.0]), prior=prior)


def test_nnpu_rejects_negative_or_missing_style_targets():
    with pytest.raises(ValueError, match=r"1 \(positive\) or 0 \(unlabeled\)"):
        nnpu_loss(torch.zeros(2), torch.tensor([1.0, -1.0]), prior=0.2)
    with pytest.raises(ValueError, match="encode unlabeled examples as 0"):
        nnpu_loss(torch.zeros(2), torch.tensor([1.0, float("nan")]), prior=0.2)

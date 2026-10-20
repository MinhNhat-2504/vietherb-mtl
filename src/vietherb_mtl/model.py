"""PyTorch multi-task baseline (PyTorch is an optional runtime dependency)."""

from __future__ import annotations

from .config import ModelConfig

try:
    import torch
    from torch import Tensor, nn
except ImportError:  # pragma: no cover - exercised only in minimal environments
    torch = None
    Tensor = object  # type: ignore[assignment,misc]
    nn = None


if nn is not None:

    class MultiTaskMLP(nn.Module):
        """Shared fingerprint trunk with one binary head per task."""

        def __init__(self, config: ModelConfig | None = None) -> None:
            super().__init__()
            self.config = config or ModelConfig()
            layers: list[nn.Module] = []
            previous = self.config.input_dim
            for width in self.config.hidden_dims:
                layers.extend(
                    [
                        nn.Linear(previous, width),
                        nn.ReLU(),
                        nn.Dropout(self.config.dropout),
                    ]
                )
                previous = width
            self.encoder = nn.Sequential(*layers)
            self.primary_heads = nn.ModuleDict(
                {task: nn.Linear(previous, 1) for task in self.config.primary_tasks}
            )
            self.auxiliary_heads = nn.ModuleDict(
                {task: nn.Linear(previous, 1) for task in self.config.auxiliary_tasks}
            )

        @property
        def task_names(self) -> tuple[str, ...]:
            return self.config.primary_tasks + self.config.auxiliary_tasks

        def encode(self, features: Tensor) -> Tensor:
            """Return shared instance embeddings for downstream MIL pooling."""

            if features.ndim != 2 or features.shape[-1] != self.config.input_dim:
                raise ValueError(
                    f"expected [batch, {self.config.input_dim}] features, "
                    f"got {tuple(features.shape)}"
                )
            return self.encoder(features)

        def forward(self, features: Tensor) -> dict[str, Tensor]:
            representation = self.encode(features)
            outputs = {
                name: head(representation).squeeze(-1) for name, head in self.primary_heads.items()
            }
            outputs.update(
                {
                    name: head(representation).squeeze(-1)
                    for name, head in self.auxiliary_heads.items()
                }
            )
            return outputs

else:

    class MultiTaskMLP:  # pragma: no cover - depends on environment
        """Import-safe placeholder that explains how to enable model training."""

        def __init__(self, config: ModelConfig | None = None) -> None:
            del config
            raise ImportError(
                "MultiTaskMLP requires PyTorch. Install torch to use the model; "
                "feature, split, and metric utilities remain available without it."
            )

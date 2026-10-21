"""Validation-only experiment selection utilities."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence


def select_validation_configuration(
    records: Sequence[Mapping[str, object]],
    *,
    parameter_names: Sequence[str],
    score_name: str = "validation_macro_pr_auc",
    maximize: bool = True,
) -> dict[str, object]:
    """Select a configuration using validation scores only."""

    if not records:
        raise ValueError("at least one validation record is required")
    if not parameter_names:
        raise ValueError("at least one parameter name is required")
    if "test" in score_name.casefold():
        raise ValueError("test metrics cannot be used for model selection")
    grouped: dict[tuple[object, ...], list[float]] = defaultdict(list)
    for index, record in enumerate(records):
        missing = [name for name in (*parameter_names, score_name) if name not in record]
        if missing:
            raise ValueError(f"validation record {index} missing fields: {missing}")
        score = float(record[score_name])
        if math.isfinite(score):
            grouped[tuple(record[name] for name in parameter_names)].append(score)
    if not grouped:
        raise ValueError("no finite validation scores")
    means = {key: sum(values) / len(values) for key, values in grouped.items() if values}
    direction = 1.0 if maximize else -1.0
    selected = min(
        means,
        key=lambda key: (
            -direction * means[key],
            json.dumps(key, sort_keys=True, default=str),
        ),
    )
    result = {name: value for name, value in zip(parameter_names, selected, strict=True)}
    result["mean_validation_score"] = means[selected]
    result["n_validation_records"] = len(grouped[selected])
    return result

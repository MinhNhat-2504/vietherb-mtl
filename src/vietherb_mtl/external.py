"""Small validation helpers for external bioactivity sources."""

from __future__ import annotations

import math
import re

NUMBER = re.compile(r"^\s*(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\s*$")


def strict_affinity(value: object) -> float | None:
    """Parse an exact positive affinity while rejecting censored relations."""

    text = str(value)
    if not NUMBER.fullmatch(text):
        return None
    parsed = float(text)
    return parsed if math.isfinite(parsed) and parsed > 0 else None

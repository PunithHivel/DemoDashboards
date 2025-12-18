from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd


def sanitize_value(value: Any):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def clean_text(value: Any) -> str | None:
    sanitized = sanitize_value(value)
    if sanitized is None:
        return None
    return str(sanitized)


def coerce_int(value: Any, *, strict: bool = False) -> int | None:
    sanitized = sanitize_value(value)
    if sanitized is None:
        return None
    try:
        return int(float(sanitized))
    except (TypeError, ValueError) as exc:
        if strict:
            raise ValueError("invalid integer") from exc
        return None


def coerce_float(value: Any) -> float | None:
    sanitized = sanitize_value(value)
    if sanitized is None:
        return None
    try:
        return float(sanitized)
    except (TypeError, ValueError):
        return None


def coerce_bool(value: Any) -> bool | None:
    sanitized = sanitize_value(value)
    if sanitized is None:
        return None
    if isinstance(sanitized, bool):
        return sanitized
    lowered = str(sanitized).strip().lower()
    if not lowered:
        return None
    return lowered in {"true", "1", "yes", "y"}


def coerce_datetime(value: Any, *, strict: bool = False) -> datetime | None:
    sanitized = sanitize_value(value)
    if sanitized is None:
        return None
    if isinstance(sanitized, datetime):
        return sanitized

    text_value = str(sanitized).strip()
    if not text_value:
        return None

    try:
        return pd.to_datetime(text_value).to_pydatetime()
    except Exception as exc:  # pragma: no cover - pandas parsing errors vary
        if strict:
            raise ValueError("invalid datetime") from exc
        return None

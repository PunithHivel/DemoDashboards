from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Set

import pandas as pd
from fastapi import HTTPException, status

from utils.parsers import coerce_bool, coerce_datetime, coerce_int, sanitize_value


def normalize_columns(df: pd.DataFrame, aliases: Mapping[str, str] | None = None) -> pd.DataFrame:
    aliases = aliases or {}
    normalized = {}
    for original in df.columns:
        key = original.strip().lower().replace(" ", "_").replace("-", "_")
        normalized[original] = aliases.get(key, key)
    return df.rename(columns=normalized)


def parse_json_value(value: Any) -> Any:
    sanitized = sanitize_value(value)
    if sanitized is None:
        return None
    if isinstance(sanitized, (dict, list)):
        return sanitized
    text = str(sanitized).strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception as exc:
        raise ValueError(f"Invalid JSON value: {text}") from exc


def prepare_rows(
    df: pd.DataFrame,
    *,
    columns: List[str],
    required_fields: Set[str],
    defaults: Mapping[str, Any] | None = None,
    aliases: Mapping[str, str] | None = None,
    int_fields: Set[str] | None = None,
    bool_fields: Set[str] | None = None,
    datetime_fields: Set[str] | None = None,
    json_fields: Set[str] | None = None,
    injected_fields: Set[str] | None = None,
    skipped_fields: Set[str] | None = None,
) -> List[Dict[str, Any]]:
    defaults = defaults or {}
    int_fields = int_fields or set()
    bool_fields = bool_fields or set()
    datetime_fields = datetime_fields or set()
    json_fields = json_fields or set()
    injected_fields = injected_fields or set()
    skipped_fields = skipped_fields or {"id"}

    df = normalize_columns(df, aliases)
    missing = [col for col in required_fields if col not in df.columns and col not in injected_fields]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV missing required columns: {', '.join(missing)}",
        )

    prepared: List[Dict[str, Any]] = []
    for record in df.to_dict(orient="records"):
        try:
            row: Dict[str, Any] = {}
            for column in columns:
                if column in injected_fields or column in skipped_fields:
                    continue
                raw = sanitize_value(record.get(column, defaults.get(column)))
                if column in int_fields and raw is not None:
                    raw = coerce_int(raw, strict=False)
                elif column in bool_fields and raw is not None:
                    raw = coerce_bool(raw)
                elif column in datetime_fields and raw is not None:
                    raw = coerce_datetime(raw, strict=False)
                elif column in json_fields and raw is not None:
                    raw = parse_json_value(raw)
                row[column] = raw

            for req in required_fields:
                if req in injected_fields:
                    continue
                if row.get(req) is None:
                    raise ValueError(f"Missing required value for '{req}'")

            prepared.append(row)
        except ValueError:
            continue

    return prepared

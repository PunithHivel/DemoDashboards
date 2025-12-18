from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from db.session import get_db_session
from repositories.commit_repository import COMMIT_COLUMNS, CommitRepository

router = APIRouter(prefix="/commit", tags=["commit"])
_repository = CommitRepository()

REQUIRED_FIELDS = {
    "hash",
    "authorid",
    "commitid",
    "repoid",
    "repositoryfullname",
    "workspaceid",
    "organizationid",
}
INT_FIELDS = {
    "authorid",
    "repoid",
    "rework",
    "newwork",
    "maintenance",
    "assistance",
    "linesadded",
    "linesremoved",
    "originalauthorid",
    "workspaceid",
    "userintegrationid",
    "estimated_storypoints",
}
BOOL_FIELDS = {
    "skippedregexfiles",
    "missingcommit",
    "processed",
    "skipfromcalculation",
    "jiramappingprocessed",
    "jiradatacollected",
    "is_auto_excluded",
}
DATETIME_FIELDS = {"date", "createddate", "modifieddate"}
DEFAULTS = {
    "skippedregexfiles": False,
    "missingcommit": False,
    "linesadded": 0,
    "linesremoved": 0,
    "processed": False,
    "skipfromcalculation": False,
    "jiramappingprocessed": False,
    "jiradatacollected": False,
    "is_auto_excluded": False,
}


def _normalize_value(value: Any):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def _parse_int(value: Any):
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        raise ValueError("invalid integer")


def _parse_bool(value: Any):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    lowered = str(value).strip().lower()
    if not lowered:
        return None
    return lowered in {"true", "1", "yes", "y"}


def _parse_datetime(value: Any):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text_value = str(value).strip()
    if not text_value:
        return None
    try:
        return pd.to_datetime(text_value).to_pydatetime()
    except Exception:
        raise ValueError("invalid datetime")


def _prepare_rows(df: pd.DataFrame) -> List[Dict]:
    missing_columns = [col for col in REQUIRED_FIELDS if col not in df.columns]
    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV missing required columns: {', '.join(missing_columns)}",
        )

    prepared: List[Dict] = []

    records = df.to_dict(orient="records")
    for idx, record in enumerate(records, start=1):
        try:
            row: Dict[str, Any] = {}
            for column in COMMIT_COLUMNS:
                raw_value = _normalize_value(record.get(column, DEFAULTS.get(column)))

                if column in INT_FIELDS and raw_value is not None:
                    raw_value = _parse_int(raw_value)
                elif column in BOOL_FIELDS and raw_value is not None:
                    raw_value = _parse_bool(raw_value)
                elif column in DATETIME_FIELDS and raw_value is not None:
                    raw_value = _parse_datetime(raw_value)

                row[column] = raw_value

            for field in REQUIRED_FIELDS:
                if row.get(field) is None:
                    raise ValueError(f"Missing required value for '{field}'")

            now = datetime.utcnow()
            row["createddate"] = row.get("createddate") or now
            row["modifieddate"] = row.get("modifieddate") or now

            prepared.append(row)
        except ValueError:
            continue

    return prepared


@router.post(
    "/csv",
    status_code=status.HTTP_201_CREATED,
    summary="Import commits from a CSV file",
)
async def import_commits_from_csv(
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV uploads are supported.",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded.",
        )

    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to parse CSV: {exc}",
        ) from exc

    rows = _prepare_rows(df)
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid commit rows found in CSV.",
        )

    inserted = _repository.bulk_insert(session, rows)
    return {
        "rows_received": len(df),
        "rows_inserted": len(inserted),
        "rows_skipped": len(df) - len(inserted),
        "commits": inserted,
    }

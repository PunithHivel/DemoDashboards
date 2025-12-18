from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from db.session import get_db_session
from repositories.pull_request_repository import PullRequestRepository
from schemas.pull_request_import import (
    BOOL_COLUMNS,
    EXPECTED_COLUMNS,
    FLOAT_COLUMNS,
    INT_COLUMNS,
    PullRequestImportResponse,
    REQUIRED_COLUMNS,
    TIMESTAMP_COLUMNS,
)
from utils.csv_loader import read_uploaded_csv
from utils.parsers import (
    clean_text,
    coerce_bool,
    coerce_datetime,
    coerce_float,
    coerce_int,
)

router = APIRouter(prefix="/pull-request-import", tags=["pull-request-import"])

_repository = PullRequestRepository()


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    alias_map = {
        "firstcommenttoapprovedduration": "firstcommenttoapproved",
        "html_link": "htmllink",
    }

    normalized = {}
    for original in df.columns:
        key = original.strip().lower().replace(" ", "").replace("-", "")
        replacement = alias_map.get(key, key)
        normalized[original] = replacement

    return df.rename(columns=normalized)


def _prepare_payloads(df: pd.DataFrame) -> Tuple[List[Dict], int]:
    df = _normalize_columns(df)

    missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV missing expected columns: {', '.join(missing)}",
        )

    if any(col not in df.columns for col in REQUIRED_COLUMNS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV missing required pull request identifiers.",
        )

    filtered = df.drop_duplicates(subset=["id"]).dropna(subset=list(REQUIRED_COLUMNS))

    payloads: List[Dict] = []
    conversion_errors = 0

    for row in filtered.itertuples(index=False):
        try:
            payload = {}
            for column in EXPECTED_COLUMNS:
                value = getattr(row, column)
                if column in TIMESTAMP_COLUMNS:
                    payload[column] = coerce_datetime(value)
                elif column in INT_COLUMNS:
                    payload[column] = coerce_int(value)
                elif column in FLOAT_COLUMNS:
                    payload[column] = coerce_float(value)
                elif column in BOOL_COLUMNS:
                    payload[column] = coerce_bool(value)
                else:
                    payload[column] = clean_text(value)

            payloads.append(payload)
        except Exception:
            conversion_errors += 1
            continue

    return payloads, conversion_errors


@router.post(
    "/csv",
    status_code=status.HTTP_201_CREATED,
    summary="Import pull requests from a CSV file",
    response_model=PullRequestImportResponse,
)
async def import_pull_requests(
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
) -> PullRequestImportResponse:
    df = await read_uploaded_csv(file)

    payloads, conversion_errors = _prepare_payloads(df)
    if not payloads:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid pull request rows found in CSV.",
        )

    inserted = _repository.bulk_upsert(session, payloads)

    return PullRequestImportResponse(
        rows_received=len(df),
        rows_inserted=inserted,
        rows_skipped=conversion_errors + (len(df) - len(payloads)),
    )

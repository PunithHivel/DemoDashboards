from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from db.session import get_db_session
from repositories.commit_repository import COMMIT_COLUMNS, CommitRepository
from schemas.commit import (
    BOOL_FIELDS,
    DATETIME_FIELDS,
    DEFAULT_COMMIT_VALUES,
    INT_FIELDS,
    REQUIRED_FIELDS,
    CommitImportResponse,
)
from utils.csv_loader import read_uploaded_csv
from utils.parsers import coerce_bool, coerce_datetime, coerce_int, sanitize_value

router = APIRouter(prefix="/commit", tags=["commit"])
_repository = CommitRepository()


def _prepare_rows(df: pd.DataFrame) -> List[Dict]:
    # Columns that will be injected from query parameters, not from CSV
    INJECTED_COLUMNS = {"organizationid", "workspaceid", "userintegrationid"}
    
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
                # Skip columns that will be injected from query parameters
                if column in INJECTED_COLUMNS:
                    continue
                    
                raw_value = sanitize_value(
                    record.get(column, DEFAULT_COMMIT_VALUES.get(column))
                )

                if column in INT_FIELDS and raw_value is not None:
                    raw_value = coerce_int(raw_value, strict=True)
                elif column in BOOL_FIELDS and raw_value is not None:
                    raw_value = coerce_bool(raw_value)
                elif column in DATETIME_FIELDS and raw_value is not None:
                    raw_value = coerce_datetime(raw_value, strict=True)

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
    response_model=CommitImportResponse,
)
async def import_commits_from_csv(
    organization_id: int = Query(..., description="Organization ID"),
    workspace_id: int = Query(..., description="Workspace ID"),
    user_integration_id: int = Query(..., description="User Integration ID"),
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
) -> CommitImportResponse:
    df = await read_uploaded_csv(file)

    rows = _prepare_rows(df)
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid commit rows found in CSV.",
        )

    # Inject organizationid, workspaceid, and userintegrationid into each row
    for row in rows:
        row["organizationid"] = organization_id
        row["workspaceid"] = workspace_id
        row["userintegrationid"] = user_integration_id

    inserted = _repository.bulk_insert(session, rows)
    return CommitImportResponse(
        rows_received=len(df),
        rows_inserted=len(inserted),
        rows_skipped=len(df) - len(inserted),
        commits=inserted,
    )

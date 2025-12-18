from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from db.session import get_db_session
from repositories.commit_repository import COMMIT_COLUMNS, CommitRepository
from schemas.commit import CommitImportResponse
from utils.csv_loader import read_uploaded_csv
from utils.parsers import coerce_bool, coerce_datetime, coerce_int, sanitize_value

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
                raw_value = sanitize_value(record.get(column, DEFAULTS.get(column)))

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

    inserted = _repository.bulk_insert(session, rows)
    return CommitImportResponse(
        rows_received=len(df),
        rows_inserted=len(inserted),
        rows_skipped=len(df) - len(inserted),
        commits=inserted,
    )

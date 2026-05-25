from __future__ import annotations

from typing import Set

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from db.session import get_db_session
from repositories.copilot_daily_summary_repository import (
    COPILOT_DAILY_SUMMARY_COLUMNS,
    CopilotDailySummaryRepository,
)
from routers._csv_import_helpers import prepare_rows
from schemas.ai_import import GenericImportResponse
from utils.csv_loader import read_uploaded_csv

router = APIRouter(prefix="/copilot-daily-summary", tags=["copilot-daily-summary"])
_repository = CopilotDailySummaryRepository()

REQUIRED_FIELDS: Set[str] = {"organizationid", "workspaceid", "date"}
INT_FIELDS: Set[str] = {"organizationid", "workspaceid", "total_active_users", "total_engaged_users"}
DATETIME_FIELDS: Set[str] = {"date"}


@router.post(
    "/csv",
    status_code=status.HTTP_201_CREATED,
    summary="Import copilot_daily_summary from CSV",
    response_model=GenericImportResponse,
)
async def import_csv(
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
) -> GenericImportResponse:
    df = await read_uploaded_csv(file)

    rows = prepare_rows(
        df,
        columns=COPILOT_DAILY_SUMMARY_COLUMNS,
        required_fields=REQUIRED_FIELDS,
        int_fields=INT_FIELDS,
        datetime_fields=DATETIME_FIELDS,
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid rows found in CSV.")

    inserted = _repository.bulk_insert(session, rows)
    inserted_count = inserted[0].get("inserted_count", 0) if inserted else 0
    return GenericImportResponse(
        rows_received=len(df),
        rows_inserted=inserted_count,
        rows_skipped=len(df) - len(rows),
    )

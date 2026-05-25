from __future__ import annotations

from datetime import datetime
from typing import Set

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from db.session import get_db_session
from repositories.cursor_daily_usage_repository import (
    CURSOR_DAILY_USAGE_COLUMNS,
    CursorDailyUsageRepository,
)
from routers._csv_import_helpers import prepare_rows
from schemas.ai_import import GenericImportResponse
from utils.csv_loader import read_uploaded_csv

router = APIRouter(prefix="/cursor-daily-usage", tags=["cursor-daily-usage"])
_repository = CursorDailyUsageRepository()

REQUIRED_FIELDS: Set[str] = {"organization_id", "email"}
INT_FIELDS: Set[str] = {
    "organization_id",
    "user_integration_id",
    "author_id",
    "total_lines_added",
    "total_lines_deleted",
    "accepted_lines_added",
    "accepted_lines_deleted",
    "total_applies",
    "total_accepts",
    "total_rejects",
    "total_tabs_shown",
    "total_tabs_accepted",
    "composer_requests",
    "chat_requests",
    "agent_requests",
    "cmdk_usages",
    "subscription_included_reqs",
    "api_key_reqs",
    "usage_based_reqs",
    "bugbot_usages",
    "original_author_id",
}
BOOL_FIELDS: Set[str] = {"is_active"}
DATETIME_FIELDS: Set[str] = {"date", "created_at", "updated_at"}


@router.post(
    "/csv",
    status_code=status.HTTP_201_CREATED,
    summary="Import cursor_daily_usage from CSV",
    response_model=GenericImportResponse,
)
async def import_csv(
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
) -> GenericImportResponse:
    df = await read_uploaded_csv(file)

    rows = prepare_rows(
        df,
        columns=CURSOR_DAILY_USAGE_COLUMNS,
        required_fields=REQUIRED_FIELDS,
        int_fields=INT_FIELDS,
        bool_fields=BOOL_FIELDS,
        datetime_fields=DATETIME_FIELDS,
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid rows found in CSV.")

    now = datetime.utcnow()
    for row in rows:
        row["created_at"] = row.get("created_at") or now
        row["updated_at"] = row.get("updated_at") or now

    inserted = _repository.bulk_insert(session, rows)
    inserted_count = inserted[0].get("inserted_count", 0) if inserted else 0
    return GenericImportResponse(
        rows_received=len(df),
        rows_inserted=inserted_count,
        rows_skipped=len(df) - len(rows),
    )

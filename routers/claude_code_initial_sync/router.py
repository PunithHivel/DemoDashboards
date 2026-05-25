from __future__ import annotations

from datetime import datetime
from typing import Set

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from db.session import get_db_session
from repositories.claude_code_initial_sync_repository import (
    CLAUDE_CODE_INITIAL_SYNC_COLUMNS,
    ClaudeCodeInitialSyncRepository,
)
from routers._csv_import_helpers import prepare_rows
from schemas.ai_import import GenericImportResponse
from utils.csv_loader import read_uploaded_csv

router = APIRouter(prefix="/claude-code-initial-sync", tags=["claude-code-initial-sync"])
_repository = ClaudeCodeInitialSyncRepository()

REQUIRED_FIELDS: Set[str] = {
    "organization_id",
    "user_integration_id",
    "sync_type",
    "sync_status",
}
INT_FIELDS: Set[str] = {"organization_id", "user_integration_id", "total_records_synced", "author_id"}
DATETIME_FIELDS: Set[str] = {
    "created_at",
    "updated_at",
    "last_sync_date",
    "sync_start_date",
    "sync_end_date",
}


@router.post(
    "/csv",
    status_code=status.HTTP_201_CREATED,
    summary="Import claude_code_initial_sync from CSV",
    response_model=GenericImportResponse,
)
async def import_csv(
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
) -> GenericImportResponse:
    df = await read_uploaded_csv(file)

    rows = prepare_rows(
        df,
        columns=CLAUDE_CODE_INITIAL_SYNC_COLUMNS,
        required_fields=REQUIRED_FIELDS,
        int_fields=INT_FIELDS,
        datetime_fields=DATETIME_FIELDS,
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid rows found in CSV.")

    now = datetime.utcnow()
    for row in rows:
        row["created_at"] = row.get("created_at") or now
        row["updated_at"] = row.get("updated_at") or now
        row["last_sync_date"] = row.get("last_sync_date") or now
        row["sync_start_date"] = row.get("sync_start_date") or now
        row["sync_end_date"] = row.get("sync_end_date") or now

    inserted = _repository.bulk_insert(session, rows)
    inserted_count = inserted[0].get("inserted_count", 0) if inserted else 0
    return GenericImportResponse(
        rows_received=len(df),
        rows_inserted=inserted_count,
        rows_skipped=len(df) - len(rows),
    )

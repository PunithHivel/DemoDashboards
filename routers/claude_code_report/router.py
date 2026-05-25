from __future__ import annotations

from datetime import datetime
from typing import Set

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from db.session import get_db_session
from repositories.claude_code_report_repository import (
    CLAUDE_CODE_REPORT_COLUMNS,
    ClaudeCodeReportRepository,
)
from routers._csv_import_helpers import prepare_rows
from schemas.ai_import import GenericImportResponse
from utils.csv_loader import read_uploaded_csv

router = APIRouter(prefix="/claude-code-report", tags=["claude-code-report"])
_repository = ClaudeCodeReportRepository()

REQUIRED_FIELDS: Set[str] = {
    "author_id",
    "actor_type",
    "organization_id",
    "user_integration_id",
    "date",
}
INT_FIELDS: Set[str] = {
    "author_id",
    "organization_id",
    "user_integration_id",
    "num_sessions",
    "lines_added",
    "lines_removed",
    "commits_by_claude_code",
    "pull_requests_by_claude_code",
    "edit_tool_accepted",
    "edit_tool_rejected",
    "write_tool_accepted",
    "write_tool_rejected",
    "multi_edit_tool_accepted",
    "multi_edit_tool_rejected",
    "notebook_edit_tool_accepted",
    "notebook_edit_tool_rejected",
    "originalauthorid",
}
DATETIME_FIELDS: Set[str] = {"date", "created_at", "updated_at"}
JSON_FIELDS: Set[str] = {"model_breakdown"}


@router.post(
    "/csv",
    status_code=status.HTTP_201_CREATED,
    summary="Import claude_code_report from CSV",
    response_model=GenericImportResponse,
)
async def import_csv(
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
) -> GenericImportResponse:
    df = await read_uploaded_csv(file)

    rows = prepare_rows(
        df,
        columns=CLAUDE_CODE_REPORT_COLUMNS,
        required_fields=REQUIRED_FIELDS,
        int_fields=INT_FIELDS,
        datetime_fields=DATETIME_FIELDS,
        json_fields=JSON_FIELDS,
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

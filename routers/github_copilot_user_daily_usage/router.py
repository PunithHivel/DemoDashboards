from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Set

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from db.session import get_db_session
from repositories.github_copilot_user_daily_usage_repository import (
    GITHUB_COPILOT_USER_DAILY_USAGE_COLUMNS,
    GitHubCopilotUserDailyUsageRepository,
)
from routers._csv_import_helpers import prepare_rows
from schemas.ai_import import GenericImportResponse
from utils.csv_loader import read_uploaded_csv

router = APIRouter(prefix="/github-copilot-user-daily-usage", tags=["github-copilot-user-daily-usage"])
_repository = GitHubCopilotUserDailyUsageRepository()

REQUIRED_FIELDS: Set[str] = {"author_id", "usage_day"}
INT_FIELDS: Set[str] = {
    "author_id",
    "original_author_id",
    "github_organization_id",
    "github_enterprise_id",
    "user_initiated_interaction_count",
    "code_generation_activity_count",
    "code_acceptance_activity_count",
    "loc_suggested_to_add_sum",
    "loc_suggested_to_delete_sum",
    "loc_added_sum",
    "loc_deleted_sum",
    "organization_id",
    "user_integration_id",
}
BOOL_FIELDS: Set[str] = {"used_agent", "used_chat"}
DATETIME_FIELDS: Set[str] = {"usage_day", "createddate", "modifieddate"}
JSON_FIELDS: Set[str] = {
    "totals_by_ide",
    "totals_by_feature",
    "totals_by_language_feature",
    "totals_by_language_model",
    "totals_by_model_feature",
}


@router.post(
    "/csv",
    status_code=status.HTTP_201_CREATED,
    summary="Import github_copilot_user_daily_usage from CSV",
    response_model=GenericImportResponse,
)
async def import_csv(
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
) -> GenericImportResponse:
    df = await read_uploaded_csv(file)

    rows = prepare_rows(
        df,
        columns=GITHUB_COPILOT_USER_DAILY_USAGE_COLUMNS,
        required_fields=REQUIRED_FIELDS,
        int_fields=INT_FIELDS,
        bool_fields=BOOL_FIELDS,
        datetime_fields=DATETIME_FIELDS,
        json_fields=JSON_FIELDS,
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid rows found in CSV.")

    now = datetime.utcnow()
    for row in rows:
        row["createddate"] = row.get("createddate") or now
        row["modifieddate"] = row.get("modifieddate") or now

    inserted = _repository.bulk_insert(session, rows)
    inserted_count = inserted[0].get("inserted_count", 0) if inserted else 0
    return GenericImportResponse(
        rows_received=len(df),
        rows_inserted=inserted_count,
        rows_skipped=len(df) - len(rows),
    )

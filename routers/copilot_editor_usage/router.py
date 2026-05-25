from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Set

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.session import get_db_session
from repositories.copilot_editor_usage_repository import (
    COPILOT_EDITOR_USAGE_COLUMNS,
    CopilotEditorUsageRepository,
)
from routers._csv_import_helpers import prepare_rows
from schemas.ai_import import GenericImportResponse
from utils.csv_loader import read_uploaded_csv

router = APIRouter(prefix="/copilot-editor-usage", tags=["copilot-editor-usage"])
_repository = CopilotEditorUsageRepository()

REQUIRED_FIELDS: Set[str] = {"organizationid", "workspaceid", "date", "editor_name"}
INT_FIELDS: Set[str] = {
    "organizationid",
    "workspaceid",
    "total_chats",
    "total_engaged_users",
    "total_chat_copy_events",
    "total_chat_insertion_events",
}
BOOL_FIELDS: Set[str] = {"is_custom_model"}
DATETIME_FIELDS: Set[str] = {"date"}
ALIASES = {
    "active_users": "total_chats",
    "engaged_users": "total_engaged_users",
}


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return pd.to_datetime(str(value)).date()
    except Exception:
        return None


def _get_daily_summary(session: Session, org_id: int, workspace_id: int, on_date: date) -> Dict[str, Any] | None:
    result = session.execute(
        text(
            """
            SELECT id, total_engaged_users
            FROM insightly.copilot_daily_summary
            WHERE organizationid = :org_id
              AND workspaceid = :workspace_id
              AND date = :on_date
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"org_id": org_id, "workspace_id": workspace_id, "on_date": on_date},
    ).mappings().first()
    return dict(result) if result else None


@router.post(
    "/csv",
    status_code=status.HTTP_201_CREATED,
    summary="Import copilot_editor_usage from CSV",
    response_model=GenericImportResponse,
)
async def import_csv(
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
) -> GenericImportResponse:
    df = await read_uploaded_csv(file)

    rows = prepare_rows(
        df,
        columns=COPILOT_EDITOR_USAGE_COLUMNS,
        required_fields=REQUIRED_FIELDS,
        int_fields=INT_FIELDS,
        bool_fields=BOOL_FIELDS,
        datetime_fields=DATETIME_FIELDS,
        aliases=ALIASES,
        injected_fields={"copilot_daily_summary_id"},
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid rows found in CSV.")

    enriched_rows = []
    for row in rows:
        on_date = _as_date(row.get("date"))
        if on_date is None:
            continue

        summary = _get_daily_summary(
            session,
            org_id=int(row["organizationid"]),
            workspace_id=int(row["workspaceid"]),
            on_date=on_date,
        )
        if summary is None:
            continue

        row["date"] = on_date
        row["copilot_daily_summary_id"] = summary["id"]
        enriched_rows.append(row)

    if not enriched_rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No rows could be linked to copilot_daily_summary.",
        )

    inserted = _repository.bulk_insert(session, enriched_rows)
    inserted_count = inserted[0].get("inserted_count", 0) if inserted else 0
    return GenericImportResponse(
        rows_received=len(df),
        rows_inserted=inserted_count,
        rows_skipped=len(df) - len(enriched_rows),
    )

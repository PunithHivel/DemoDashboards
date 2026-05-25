from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Set

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.session import get_db_session
from repositories.copilot_language_usage_repository import (
    COPILOT_LANGUAGE_USAGE_COLUMNS,
    CopilotLanguageUsageRepository,
)
from routers._csv_import_helpers import prepare_rows
from schemas.ai_import import GenericImportResponse
from utils.csv_loader import read_uploaded_csv

router = APIRouter(prefix="/copilot-language-usage", tags=["copilot-language-usage"])
_repository = CopilotLanguageUsageRepository()

REQUIRED_FIELDS: Set[str] = {"organizationid", "workspaceid", "date", "language_name"}
INT_FIELDS: Set[str] = {
    "organizationid",
    "workspaceid",
    "total_engaged_users",
    "total_code_acceptances",
    "total_code_suggestions",
    "total_code_lines_accepted",
    "total_code_lines_suggested",
}
DATETIME_FIELDS: Set[str] = {"date"}
ALIASES = {
    "language": "language_name",
    "code_generation_count": "total_code_suggestions",
    "code_acceptance_count": "total_code_acceptances",
    "loc_suggested": "total_code_lines_suggested",
    "loc_accepted": "total_code_lines_accepted",
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
    summary="Import copilot_language_usage from CSV",
    response_model=GenericImportResponse,
)
async def import_csv(
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
) -> GenericImportResponse:
    df = await read_uploaded_csv(file)

    rows = prepare_rows(
        df,
        columns=COPILOT_LANGUAGE_USAGE_COLUMNS,
        required_fields=REQUIRED_FIELDS,
        int_fields=INT_FIELDS,
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
        row["editor_name"] = row.get("editor_name") or "unknown"
        row["model_name"] = row.get("model_name") or "unknown"
        row["total_engaged_users"] = row.get("total_engaged_users") or summary.get("total_engaged_users")
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

from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from .bulk_copy import bulk_copy_insert

COPILOT_DAILY_SUMMARY_COLUMNS = [

    "organizationid",
    "workspaceid",
    "date",
    "total_active_users",
    "total_engaged_users",

]


class CopilotDailySummaryRepository:
    """Handles copilot_daily_summary table inserts using PostgreSQL COPY."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        if not rows:
            return []

        count = bulk_copy_insert(
            session=session,
            table_name="copilot_daily_summary",
            columns=COPILOT_DAILY_SUMMARY_COLUMNS,
            rows=rows,
        )
        return [{"inserted_count": count}]

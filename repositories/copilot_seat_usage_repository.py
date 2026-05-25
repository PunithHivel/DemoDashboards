from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from .bulk_copy import bulk_copy_insert

COPILOT_SEAT_USAGE_COLUMNS = [

    "organizationid",
    "workspaceid",
    "assignee_id",
    "assignee_login",
    "plan_type",
    "last_activity_editor",
    "last_activity_at",
    "created_at",
    "updated_at",
    "pending_cancellation_date",
    "date",

]


class CopilotSeatUsageRepository:
    """Handles copilot_seat_usage table inserts using PostgreSQL COPY."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        if not rows:
            return []

        count = bulk_copy_insert(
            session=session,
            table_name="copilot_seat_usage",
            columns=COPILOT_SEAT_USAGE_COLUMNS,
            rows=rows,
        )
        return [{"inserted_count": count}]

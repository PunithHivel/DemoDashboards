from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from .bulk_copy import bulk_copy_insert

COPILOT_EDITOR_USAGE_COLUMNS = [

    "copilot_daily_summary_id",
    "organizationid",
    "workspaceid",
    "date",
    "editor_name",
    "model_name",
    "total_chats",
    "is_custom_model",
    "total_engaged_users",
    "total_chat_copy_events",
    "total_chat_insertion_events",

]


class CopilotEditorUsageRepository:
    """Handles copilot_editor_usage table inserts using PostgreSQL COPY."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        if not rows:
            return []

        count = bulk_copy_insert(
            session=session,
            table_name="copilot_editor_usage",
            columns=COPILOT_EDITOR_USAGE_COLUMNS,
            rows=rows,
        )
        return [{"inserted_count": count}]

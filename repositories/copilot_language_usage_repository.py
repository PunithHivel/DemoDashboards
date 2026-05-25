from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from .bulk_copy import bulk_copy_insert

COPILOT_LANGUAGE_USAGE_COLUMNS = [

    "copilot_daily_summary_id",
    "organizationid",
    "workspaceid",
    "date",
    "editor_name",
    "model_name",
    "language_name",
    "total_engaged_users",
    "total_code_acceptances",
    "total_code_suggestions",
    "total_code_lines_accepted",
    "total_code_lines_suggested",

]


class CopilotLanguageUsageRepository:
    """Handles copilot_language_usage table inserts using PostgreSQL COPY."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        if not rows:
            return []

        count = bulk_copy_insert(
            session=session,
            table_name="copilot_language_usage",
            columns=COPILOT_LANGUAGE_USAGE_COLUMNS,
            rows=rows,
        )
        return [{"inserted_count": count}]

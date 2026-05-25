from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from .bulk_copy import bulk_copy_insert

CLAUDE_CODE_REPORT_COLUMNS = [

    "author_id",
    "actor_type",
    "organization_id",
    "user_integration_id",
    "terminal_type",
    "customer_type",
    "subscription_type",
    "date",
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
    "model_breakdown",
    "created_at",
    "updated_at",
    "originalauthorid",

]


class ClaudeCodeReportRepository:
    """Handles claude_code_report table inserts using PostgreSQL COPY."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        if not rows:
            return []

        count = bulk_copy_insert(
            session=session,
            table_name="claude_code_report",
            columns=CLAUDE_CODE_REPORT_COLUMNS,
            rows=rows,
        )
        return [{"inserted_count": count}]

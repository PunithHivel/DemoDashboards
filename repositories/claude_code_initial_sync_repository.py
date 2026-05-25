from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from .bulk_copy import bulk_copy_insert

CLAUDE_CODE_INITIAL_SYNC_COLUMNS = [

    "organization_id",
    "user_integration_id",
    "sync_type",
    "sync_status",
    "error_message",
    "created_at",
    "updated_at",
    "last_sync_date",
    "sync_start_date",
    "sync_end_date",
    "total_records_synced",
    "email",
    "author_id",

]


class ClaudeCodeInitialSyncRepository:
    """Handles claude_code_initial_sync table inserts using PostgreSQL COPY."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        if not rows:
            return []

        count = bulk_copy_insert(
            session=session,
            table_name="claude_code_initial_sync",
            columns=CLAUDE_CODE_INITIAL_SYNC_COLUMNS,
            rows=rows,
        )
        return [{"inserted_count": count}]

from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from .bulk_copy import bulk_copy_insert

CURSOR_INITIAL_SYNC_COLUMNS = [

    "organization_id",
    "user_integration_id",
    "sync_type",
    "sync_status",
    "error_message",
    "created_at",
    "updated_at",
    "from_date",
    "to_date",

]


class CursorInitialSyncRepository:
    """Handles cursor_initial_sync table inserts using PostgreSQL COPY."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        if not rows:
            return []

        count = bulk_copy_insert(
            session=session,
            table_name="cursor_initial_sync",
            columns=CURSOR_INITIAL_SYNC_COLUMNS,
            rows=rows,
        )
        return [{"inserted_count": count}]

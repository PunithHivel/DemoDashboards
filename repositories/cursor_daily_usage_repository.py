from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from .bulk_copy import bulk_copy_insert

CURSOR_DAILY_USAGE_COLUMNS = [

    "organization_id",
    "user_integration_id",
    "author_id",
    "email",
    "date",
    "formatted_date",
    "is_active",
    "total_lines_added",
    "total_lines_deleted",
    "accepted_lines_added",
    "accepted_lines_deleted",
    "total_applies",
    "total_accepts",
    "total_rejects",
    "total_tabs_shown",
    "total_tabs_accepted",
    "composer_requests",
    "chat_requests",
    "agent_requests",
    "cmdk_usages",
    "subscription_included_reqs",
    "api_key_reqs",
    "usage_based_reqs",
    "bugbot_usages",
    "most_used_model",
    "apply_most_used_extension",
    "tab_most_used_extension",
    "client_version",
    "created_at",
    "updated_at",
    "original_author_id",

]


class CursorDailyUsageRepository:
    """Handles cursor_daily_usage table inserts using PostgreSQL COPY."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        if not rows:
            return []

        count = bulk_copy_insert(
            session=session,
            table_name="cursor_daily_usage",
            columns=CURSOR_DAILY_USAGE_COLUMNS,
            rows=rows,
        )
        return [{"inserted_count": count}]

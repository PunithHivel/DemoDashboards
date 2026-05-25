from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from .bulk_copy import bulk_copy_insert

CURSOR_SPENDING_COLUMNS = [

    "organization_id",
    "user_integration_id",
    "author_id",
    "email",
    "name",
    "role",
    "spend_cents",
    "fast_premium_requests",
    "hard_limit_override_dollars",
    "subscription_cycle_start",
    "created_at",
    "updated_at",
    "original_author_id",
    "first_seen_in_billing_cycle",
    "last_seen_in_billing_cycle",

]


class CursorSpendingRepository:
    """Handles cursor_spending table inserts using PostgreSQL COPY."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        if not rows:
            return []

        count = bulk_copy_insert(
            session=session,
            table_name="cursor_spending",
            columns=CURSOR_SPENDING_COLUMNS,
            rows=rows,
        )
        return [{"inserted_count": count}]

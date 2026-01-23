from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from .bulk_copy import bulk_copy_insert

CHANGE_REQUESTS_COLUMNS = [
    "event_id",
    "event_type",
    "outage_incident_number",
    "createddate",
    "modifieddate",
    "start_date",
    "end_date",
    "organization_id",
    "assignment_group",
    "caused_by_azdo_item",
    "caused_by_change",
    "team_id",
    "close_code",
    "duration",
    "authorid",
    "repoid",
]


class ChangeRequestsRepository:
    """Handles change_requests table inserts using high-performance COPY."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        """
        Bulk insert change requests using PostgreSQL COPY command.
        
        This is 10-100x faster than row-by-row inserts.
        Returns summary of inserted rows (not individual IDs due to COPY limitations).
        """
        if not rows:
            return []

        count = bulk_copy_insert(
            session=session,
            table_name="change_requests",
            columns=CHANGE_REQUESTS_COLUMNS,
            rows=rows,
        )
        
        # Return summary since COPY doesn't support RETURNING
        return [{"inserted_count": count}]

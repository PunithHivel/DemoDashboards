from __future__ import annotations

from typing import Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

CHANGE_REQUESTS_INSERT_SQL = text(
    """
    INSERT INTO insightly.change_requests (
        event_id,
        event_type,
        outage_incident_number,
        createddate,
        modifieddate,
        start_date,
        end_date,
        organization_id,
        assignment_group,
        caused_by_azdo_item,
        caused_by_change,
        team_id,
        close_code,
        duration,
        authorid,
        repoid
    ) VALUES (
        :event_id,
        :event_type,
        :outage_incident_number,
        :createddate,
        :modifieddate,
        :start_date,
        :end_date,
        :organization_id,
        :assignment_group,
        :caused_by_azdo_item,
        :caused_by_change,
        :team_id,
        :close_code,
        :duration,
        :authorid,
        :repoid
    )
    RETURNING id
    """
)


class ChangeRequestsRepository:
    """Handles change_requests table inserts."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        if not rows:
            return []

        inserted: List[Dict] = []
        for row in rows:
            result = session.execute(CHANGE_REQUESTS_INSERT_SQL, row)
            inserted.append(dict(result.mappings().one()))

        return inserted

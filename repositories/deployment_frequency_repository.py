from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from .bulk_copy import bulk_copy_insert

DEPLOYMENT_FREQUENCY_COLUMNS = [
    "deployment_record_id",
    "start_date",
    "end_date",
    "environment_id",
    "owner_id",
    "result",
    "pipeline_id",
    "organization_id",
    "user_integration_id",
    "created_date",
    "modified_date",
    "authorid",
    "originalauthorid",
    "repoid",
    "team_id",
    "release_date",
]


class DeploymentFrequencyRepository:
    """Handles deployment_frequency table inserts using high-performance COPY."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        """
        Bulk insert deployment frequency records using PostgreSQL COPY command.
        
        This is 10-100x faster than row-by-row inserts.
        Returns summary of inserted rows (not individual IDs due to COPY limitations).
        """
        if not rows:
            return []

        count = bulk_copy_insert(
            session=session,
            table_name="deployment_frequency",
            columns=DEPLOYMENT_FREQUENCY_COLUMNS,
            rows=rows,
        )
        
        # Return summary since COPY doesn't support RETURNING
        return [{"inserted_count": count}]

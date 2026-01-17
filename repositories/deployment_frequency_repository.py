from __future__ import annotations

from typing import Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

DEPLOYMENT_FREQUENCY_INSERT_SQL = text(
    """
    INSERT INTO insightly.deployment_frequency (
        deployment_record_id,
        start_date,
        end_date,
        environment_id,
        owner_id,
        result,
        pipeline_id,
        organization_id,
        user_integration_id,
        created_date,
        modified_date,
        authorid,
        originalauthorid,
        repoid,
        team_id,
        release_date
    ) VALUES (
        :deployment_record_id,
        :start_date,
        :end_date,
        :environment_id,
        :owner_id,
        :result,
        :pipeline_id,
        :organization_id,
        :user_integration_id,
        :created_date,
        :modified_date,
        :authorid,
        :originalauthorid,
        :repoid,
        :team_id,
        :release_date
    )
    RETURNING id
    """
)


class DeploymentFrequencyRepository:
    """Handles deployment_frequency table inserts."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        if not rows:
            return []

        inserted: List[Dict] = []
        for row in rows:
            result = session.execute(DEPLOYMENT_FREQUENCY_INSERT_SQL, row)
            inserted.append(dict(result.mappings().one()))

        return inserted

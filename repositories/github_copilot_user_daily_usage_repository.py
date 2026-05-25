from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from .bulk_copy import bulk_copy_insert

GITHUB_COPILOT_USER_DAILY_USAGE_COLUMNS = [

    "author_id",
    "original_author_id",
    "github_organization_id",
    "github_enterprise_id",
    "usage_day",
    "user_initiated_interaction_count",
    "code_generation_activity_count",
    "code_acceptance_activity_count",
    "loc_suggested_to_add_sum",
    "loc_suggested_to_delete_sum",
    "loc_added_sum",
    "loc_deleted_sum",
    "used_agent",
    "used_chat",
    "totals_by_ide",
    "totals_by_feature",
    "totals_by_language_feature",
    "totals_by_language_model",
    "totals_by_model_feature",
    "organization_id",
    "user_integration_id",
    "createddate",
    "modifieddate",

]


class GitHubCopilotUserDailyUsageRepository:
    """Handles github_copilot_user_daily_usage table inserts using PostgreSQL COPY."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        if not rows:
            return []

        count = bulk_copy_insert(
            session=session,
            table_name="github_copilot_user_daily_usage",
            columns=GITHUB_COPILOT_USER_DAILY_USAGE_COLUMNS,
            rows=rows,
        )
        return [{"inserted_count": count}]

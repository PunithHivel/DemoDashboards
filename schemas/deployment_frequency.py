from typing import Any, Dict, List, Set

from pydantic import BaseModel

REQUIRED_FIELDS: Set[str] = {
    "deployment_record_id",
    "start_date",
    "end_date",
    "result",
}

INT_FIELDS: Set[str] = {
    "deployment_record_id",
    "environment_id",
    "owner_id",
    "pipeline_id",
    "authorid",
    "originalauthorid",
    "repoid",
    "team_id",
}

DATETIME_FIELDS: Set[str] = {
    "start_date",
    "end_date",
    "created_date",
    "modified_date",
    "release_date",
}

DEFAULT_DEPLOYMENT_FREQUENCY_VALUES: Dict[str, Any] = {}


class DeploymentFrequencyImportResponse(BaseModel):
    rows_received: int
    rows_inserted: int
    rows_skipped: int
    organization_id: int
    user_integration_id: int

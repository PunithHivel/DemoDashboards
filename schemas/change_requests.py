from typing import Any, Dict, List, Set

from pydantic import BaseModel

REQUIRED_FIELDS: Set[str] = {
    "event_id",
    "event_type",
    "start_date",
    "end_date",
}

INT_FIELDS: Set[str] = {
    "duration",
    "authorid",
    "repoid",
    "team_id",
}

DATETIME_FIELDS: Set[str] = {
    "createddate",
    "modifieddate",
    "start_date",
    "end_date",
}

DEFAULT_CHANGE_REQUESTS_VALUES: Dict[str, Any] = {}


class ChangeRequestsImportResponse(BaseModel):
    rows_received: int
    rows_inserted: int
    rows_skipped: int
    organization_id: int

from typing import Any, Dict, List, Set

from pydantic import BaseModel

REQUIRED_FIELDS: Set[str] = {
    "repoid",
}

INT_FIELDS: Set[str] = {
    "authorid",
    "pullrequestid",
    "commitid",
    "repoid",
    "originalauthorid",
}

DATETIME_FIELDS: Set[str] = {"date", "createddate", "modifieddate"}

DEFAULT_PR_UPDATE_VALUES: Dict[str, Any] = {}


class PrUpdateImportResponse(BaseModel):
    rows_received: int
    rows_inserted: int
    rows_skipped: int
    pr_updates: List[Dict[str, Any]]

from typing import Any, Dict, List, Set

from pydantic import BaseModel

REQUIRED_FIELDS: Set[str] = {
    "pullrequestid",
    "authorid",
}

INT_FIELDS: Set[str] = {
    "pullrequestid",
    "authorid",
    "originalauthorid",
    "repoid",
}

BOOL_FIELDS: Set[str] = {
    "approved",
}

DATETIME_FIELDS: Set[str] = {"approveddate", "createddate", "modifieddate"}

DEFAULT_PR_REVIEWER_VALUES: Dict[str, Any] = {
    "approved": False,
}


class PrReviewerImportResponse(BaseModel):
    rows_received: int
    rows_inserted: int
    rows_skipped: int
    pr_reviewers: List[Dict[str, Any]]

from typing import Any, Dict, List, Set

from pydantic import BaseModel

REQUIRED_FIELDS: Set[str] = {
    "pullrequestid",
    "authorid",
    "createdon",
}

INT_FIELDS: Set[str] = {
    "commentid",
    "authorid",
    "pullrequestid",
    "originalauthorid",
    "threadid",
    "sentimentscore",
}

BOOL_FIELDS: Set[str] = {
    "deleted",
    "sentimentprocessed",
}

DATETIME_FIELDS: Set[str] = {"createdon", "updatedon", "createddate", "modifieddate"}

DEFAULT_PR_COMMENT_VALUES: Dict[str, Any] = {
    "deleted": False,
}


class PrCommentImportResponse(BaseModel):
    rows_received: int
    rows_inserted: int
    rows_skipped: int
    pr_comments: List[Dict[str, Any]]

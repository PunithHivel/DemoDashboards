from typing import Any, Dict, List, Set

from pydantic import BaseModel

REQUIRED_FIELDS: Set[str] = {
    "hash",
    "authorid",
    "commitid",
    "repoid",
    "repositoryfullname",
    "workspaceid",
    "organizationid",
}

INT_FIELDS: Set[str] = {
    "authorid",
    "repoid",
    "rework",
    "newwork",
    "maintenance",
    "assistance",
    "linesadded",
    "linesremoved",
    "originalauthorid",
    "workspaceid",
    "userintegrationid",
    "estimated_storypoints",
}

BOOL_FIELDS: Set[str] = {
    "skippedregexfiles",
    "missingcommit",
    "processed",
    "skipfromcalculation",
    "jiramappingprocessed",
    "jiradatacollected",
    "is_auto_excluded",
}

DATETIME_FIELDS: Set[str] = {"date", "createddate", "modifieddate"}

DEFAULT_COMMIT_VALUES: Dict[str, Any] = {
    "skippedregexfiles": False,
    "missingcommit": False,
    "linesadded": 0,
    "linesremoved": 0,
    "processed": False,
    "skipfromcalculation": False,
    "jiramappingprocessed": False,
    "jiradatacollected": False,
    "is_auto_excluded": False,
}


class CommitImportResponse(BaseModel):
    rows_received: int
    rows_inserted: int
    rows_skipped: int
    commits: List[Dict[str, Any]]

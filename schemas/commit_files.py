from typing import Any, Dict, List, Set

from pydantic import BaseModel

REQUIRED_FIELDS: Set[str] = {
    "commitid",
    "repopathname",
}

INT_FIELDS: Set[str] = {
    "commitid",
    "linesadded",
    "linesremoved",
    "newwork",
    "rework",
    "maintenance",
    "assistance",
}

BOOL_FIELDS: Set[str] = {
    "skippedfromcalculation",
}

DATETIME_FIELDS: Set[str] = {"createddate", "modifieddate"}

DEFAULT_COMMIT_FILES_VALUES: Dict[str, Any] = {
    "linesadded": 0,
    "linesremoved": 0,
    "skippedfromcalculation": False,
}


class CommitFilesImportResponse(BaseModel):
    rows_received: int
    rows_inserted: int
    rows_skipped: int
    commit_files: List[Dict[str, Any]]

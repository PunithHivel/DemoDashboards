from typing import Any, Dict, List

from pydantic import BaseModel


class CommitImportResponse(BaseModel):
    rows_received: int
    rows_inserted: int
    rows_skipped: int
    commits: List[Dict[str, Any]]

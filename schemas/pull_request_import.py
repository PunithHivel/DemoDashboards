from pydantic import BaseModel


class PullRequestImportResponse(BaseModel):
    rows_received: int
    rows_inserted: int
    rows_skipped: int

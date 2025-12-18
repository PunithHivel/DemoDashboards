from pydantic import BaseModel


class AuthorImportResponse(BaseModel):
    rows_received: int
    rows_inserted: int
    rows_skipped: int
    organization_id: int

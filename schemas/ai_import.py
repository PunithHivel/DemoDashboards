from pydantic import BaseModel


class GenericImportResponse(BaseModel):
    rows_received: int
    rows_inserted: int
    rows_skipped: int

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AuthorInjectRequest(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    type: Optional[str] = None
    scmprovider: Optional[str] = None
    active: Optional[bool] = None
    archived: Optional[bool] = None
    generated: Optional[bool] = None
    labels: Optional[Dict[str, Any]] = None


class AuthorInjectResponse(BaseModel):
    status: str
    total_processed: int
    inserted: int
    skipped: int
    organization_id: int
    inserted_authors: list = Field(default_factory=list)
    progress_percent: int = 0

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class RepoSeedRequest(BaseModel):
    count: int = Field(5, ge=1, le=50)
    workspace_id: int = Field(7172, ge=1)


class RepoSeedResponse(BaseModel):
    workspace_id: int
    count: int
    repos: List[Dict[str, Any]]

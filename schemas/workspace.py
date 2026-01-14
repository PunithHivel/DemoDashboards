from pydantic import BaseModel


class WorkspaceRequest(BaseModel):
    name: str
    slug: str


class WorkspaceResponse(BaseModel):
    workspace_id: int
    name: str
    slug: str

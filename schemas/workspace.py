from pydantic import BaseModel


class WorkspaceResponse(BaseModel):
    workspace_id: int
    name: str
    slug: str

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from db.session import get_db_session
from repositories.workspace_repository import WorkspaceRepository

router = APIRouter(prefix="/workspace", tags=["workspace"])
_repository = WorkspaceRepository()


@router.post(
    "/workspace",
    status_code=status.HTTP_201_CREATED,
    summary="Create a dummy workspace with name/slug set to 'testing'",
)
def create_dummy_workspace(session: Session = Depends(get_db_session)):
    workspace_id = _repository.create_dummy_workspace(session)
    return {"workspace_id": workspace_id, "name": "testing", "slug": "testing"}

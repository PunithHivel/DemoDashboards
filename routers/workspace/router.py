from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from db.session import get_db_session
from repositories.workspace_repository import WorkspaceRepository
from schemas.workspace import WorkspaceResponse

router = APIRouter(prefix="/workspace", tags=["workspace"])
_repository = WorkspaceRepository()


@router.post(
    "/workspace",
    status_code=status.HTTP_201_CREATED,
    summary="Create a dummy workspace with name/slug set to 'testing'",
    response_model=WorkspaceResponse,
)
def create_dummy_workspace(
    session: Session = Depends(get_db_session),
) -> WorkspaceResponse:
    workspace_id = _repository.create_dummy_workspace(session)
    return WorkspaceResponse(workspace_id=workspace_id, name="testing", slug="testing")

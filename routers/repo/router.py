from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.session import get_db_session
from repositories.repo_repository import RepoRepository


class RepoSeedRequest(BaseModel):
    count: int = Field(5, ge=1, le=50)
    workspace_id: int = Field(7172, ge=1)


router = APIRouter(prefix="/repo", tags=["repo"])
_repository = RepoRepository()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create dummy repositories for the provided workspace",
)
def create_dummy_repos(
    request: RepoSeedRequest,
    session: Session = Depends(get_db_session),
):
    try:
        created = _repository.create_dummy_repos(
            session, workspace_id=request.workspace_id, count=request.count
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc

    return {
        "workspace_id": request.workspace_id,
        "count": len(created),
        "repos": created,
    }

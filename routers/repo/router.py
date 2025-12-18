from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db_session
from repositories.repo_repository import RepoRepository
from schemas.repo import RepoSeedRequest, RepoSeedResponse


router = APIRouter(prefix="/repo", tags=["repo"])
_repository = RepoRepository()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create dummy repositories for the provided workspace",
    response_model=RepoSeedResponse,
)
def create_dummy_repos(
    request: RepoSeedRequest,
    session: Session = Depends(get_db_session),
) -> RepoSeedResponse:
    try:
        created = _repository.create_dummy_repos(
            session, workspace_id=request.workspace_id, count=request.count
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc

    return RepoSeedResponse(
        workspace_id=request.workspace_id,
        count=len(created),
        repos=created,
    )

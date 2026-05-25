from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db_session
from repositories.repo_repository import RepoRepository
from schemas.repo import RepoListResponse, RepoSeedRequest, RepoSeedResponse


router = APIRouter(prefix="/repo", tags=["repo"])
_repository = RepoRepository()


@router.get(
    "/check",
    status_code=status.HTTP_200_OK,
    summary="Check if repo table exists and fetch repos for an organization",
)
def check_repo_table(
    organization_id: int,
    workspace_id: int | None = None,
    session: Session = Depends(get_db_session),
):
    table_exists, repos = _repository.check_table_and_list_repos(
        session, organization_id=organization_id, workspace_id=workspace_id
    )
    
    return {
        "table_exists": table_exists,
        "organization_id": organization_id,
        "workspace_id": workspace_id,
        "repos_count": len(repos),
        "repos": repos,
    }


@router.get(
    "/list",
    status_code=status.HTTP_200_OK,
    summary="List repositories for an organization",
    response_model=RepoListResponse,
)
def list_repos(
    organization_id: int,
    workspace_id: int | None = None,
    session: Session = Depends(get_db_session),
) -> RepoListResponse:
    repos = _repository.list_repos(
        session, organization_id=organization_id, workspace_id=workspace_id
    )
    return RepoListResponse(
        organization_id=organization_id,
        workspace_id=workspace_id,
        repos=repos,
    )


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
            session, 
            workspace_id=request.workspace_id, 
            count=request.count,
            organization_id=request.organization_id,
            user_integration_id=request.user_integration_id,
            owner=request.owner
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

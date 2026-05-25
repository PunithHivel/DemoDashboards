from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from db.session import get_db_session
from repositories.lookup_repository import LookupRepository
from schemas.lookup import AuthorListResponse, TeamAuthorsResponse, TeamListResponse


router = APIRouter(prefix="/lookup", tags=["lookup"])
_repository = LookupRepository()


@router.get("/teams", status_code=status.HTTP_200_OK, response_model=TeamListResponse)
def list_teams(
    organization_id: int,
    session: Session = Depends(get_db_session),
) -> TeamListResponse:
    teams = _repository.list_teams(session, organization_id)
    return TeamListResponse(organization_id=organization_id, teams=teams)


@router.get("/authors", status_code=status.HTTP_200_OK, response_model=AuthorListResponse)
def list_authors(
    organization_id: int,
    session: Session = Depends(get_db_session),
) -> AuthorListResponse:
    authors = _repository.list_authors(session, organization_id)
    return AuthorListResponse(organization_id=organization_id, authors=authors)


@router.get(
    "/teams/{team_id}/authors",
    status_code=status.HTTP_200_OK,
    response_model=TeamAuthorsResponse,
)
def list_team_authors(
    team_id: int,
    organization_id: int,
    session: Session = Depends(get_db_session),
) -> TeamAuthorsResponse:
    authors = _repository.list_team_authors(session, organization_id, team_id)
    return TeamAuthorsResponse(
        organization_id=organization_id, team_id=team_id, authors=authors
    )

from typing import List, Optional

from pydantic import BaseModel


class TeamListItem(BaseModel):
    id: int
    name: Optional[str] = None
    organizationid: int


class AuthorListItem(BaseModel):
    id: int
    name: Optional[str] = None
    username: Optional[str] = None
    organizationid: int


class TeamListResponse(BaseModel):
    organization_id: int
    teams: List[TeamListItem]


class AuthorListResponse(BaseModel):
    organization_id: int
    authors: List[AuthorListItem]


class TeamAuthorsResponse(BaseModel):
    organization_id: int
    team_id: int
    authors: List[AuthorListItem]

from typing import Dict, Set

from pydantic import BaseModel

ORG_ID = 2159
CSV_TO_DB_FIELDS: Dict[str, str] = {
    "unique_ic": "accountid",
    "name": "name",
    "email": "email",
    "labels": "labels",
    "username": "username",
    "login_via": "type",
    "user_role": "access_status",
    "teams": "sharedteams",
    "scm_provider": "scmprovider",
    "id": "id",
}
REQUIRED_NON_NULL: Set[str] = {"id", "scm_provider", "name", "username", "login_via"}


class AuthorImportResponse(BaseModel):
    rows_received: int
    rows_inserted: int
    rows_skipped: int
    organization_id: int

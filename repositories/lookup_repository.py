from __future__ import annotations

from typing import Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session


TEAM_LIST_SQL = text(
    """
    SELECT id, name, organizationid
    FROM insightly.team
    WHERE organizationid = :organization_id
    ORDER BY id
    """
)

AUTHOR_LIST_SQL = text(
    """
    SELECT id,
           aes_decrypt(name) AS name,
           aes_decrypt(username) AS username,
           organizationid
    FROM insightly.author
    WHERE organizationid = :organization_id
    ORDER BY id
    """
)

TEAM_AUTHORS_SQL = text(
    """
    SELECT a.id,
           aes_decrypt(a.name) AS name,
           aes_decrypt(a.username) AS username,
           a.organizationid
    FROM insightly.teamauthorrelation tar
    JOIN insightly.author a
      ON a.id = tar.authorid
     AND a.organizationid = tar.organizationid
    WHERE tar.organizationid = :organization_id
      AND tar.teamid = :team_id
      AND (tar.exitdate IS NULL OR tar.exitdate > NOW())
    ORDER BY a.id
    """
)


class LookupRepository:
    def list_teams(self, session: Session, organization_id: int) -> List[Dict]:
        rows = session.execute(TEAM_LIST_SQL, {"organization_id": organization_id}).mappings().all()
        return [dict(row) for row in rows]

    def list_authors(self, session: Session, organization_id: int) -> List[Dict]:
        rows = session.execute(AUTHOR_LIST_SQL, {"organization_id": organization_id}).mappings().all()
        return [dict(row) for row in rows]

    def list_team_authors(self, session: Session, organization_id: int, team_id: int) -> List[Dict]:
        rows = session.execute(
            TEAM_AUTHORS_SQL, {"organization_id": organization_id, "team_id": team_id}
        ).mappings().all()
        return [dict(row) for row in rows]

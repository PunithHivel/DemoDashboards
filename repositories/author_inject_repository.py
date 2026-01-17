from __future__ import annotations

from typing import Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

AUTHOR_INJECT_INSERT_SQL = text(
    """
    INSERT INTO insightly.author (
        name,
        username,
        email,
        type,
        scmprovider,
        active,
        archived,
        generated,
        labels,
        organizationid
    ) VALUES (
        aes_encrypt(:name),
        aes_encrypt(:username),
        CASE
            WHEN :email IS NULL THEN NULL
            ELSE aes_encrypt(:email)
        END,
        :type,
        :scmprovider,
        :active,
        :archived,
        :generated,
        CAST(:labels AS jsonb),
        :organizationid
    )
    RETURNING id, aes_decrypt(name) as name, aes_decrypt(username) as username, 
              CASE WHEN email IS NULL THEN NULL ELSE aes_decrypt(email) END as email, 
              organizationid
    """
)


class AuthorInjectRepository:
    """Handles author table inserts for injection endpoint."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        if not rows:
            return []

        inserted: List[Dict] = []
        for row in rows:
            result = session.execute(AUTHOR_INJECT_INSERT_SQL, row)
            inserted.append(dict(result.mappings().one()))

        return inserted

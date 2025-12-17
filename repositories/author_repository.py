from __future__ import annotations

from typing import Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session


AUTHOR_INSERT_SQL = text(
    """
    INSERT INTO insightly.author (
        id,
        organizationid,
        accountid,
        name,
        email,
        labels,
        username,
        type,
        access_status,
        sharedteams,
        scmprovider,
        active
    ) VALUES (
        :id,
        :organizationid,
        :accountid,
        aes_encrypt(:name),
        CASE
            WHEN :email IS NULL THEN NULL
            ELSE aes_encrypt(:email)
        END,
        CAST(:labels AS jsonb),
        aes_encrypt(:username),
        :login_via,
        :access_status,
        :sharedteams,
        :scmprovider,
        :active
    )
    ON CONFLICT (id, organizationid)
    DO UPDATE SET
        accountid = EXCLUDED.accountid,
        name = aes_encrypt(:name),
        email = CASE
            WHEN :email IS NULL THEN NULL
            ELSE aes_encrypt(:email)
        END,
        labels = EXCLUDED.labels,
        username = aes_encrypt(:username),
        type = EXCLUDED.type,
        access_status = EXCLUDED.access_status,
        sharedteams = EXCLUDED.sharedteams,
        scmprovider = EXCLUDED.scmprovider,
        active = EXCLUDED.active,
        modifieddate = CURRENT_TIMESTAMP
    """
)


class AuthorRepository:
    """Encapsulates the SQL needed to upsert author rows safely."""

    def bulk_upsert(
        self,
        session: Session,
        author_payloads: Sequence[Mapping],
    ) -> int:
        if not author_payloads:
            return 0

        session.execute(AUTHOR_INSERT_SQL, author_payloads)
        # flush/commit handled by caller session management
        return len(author_payloads)

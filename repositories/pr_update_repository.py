from __future__ import annotations

from typing import Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

PR_UPDATE_COLUMNS = [
    "authorid",
    "date",
    "pullrequestid",
    "commitid",
    "repoid",
    "field",
    "action",
    "oldvalue",
    "newvalue",
    "originalauthorid",
    "createddate",
    "modifieddate",
    "organizationid",
    "userintegrationid",
]

PR_UPDATE_INSERT_SQL = text(
    """
    INSERT INTO insightly.pr_update (
        authorid,
        date,
        pullrequestid,
        commitid,
        repoid,
        field,
        action,
        oldvalue,
        newvalue,
        originalauthorid,
        createddate,
        modifieddate,
        organizationid,
        userintegrationid
    ) VALUES (
        :authorid,
        :date,
        :pullrequestid,
        :commitid,
        :repoid,
        :field,
        :action,
        :oldvalue,
        :newvalue,
        :originalauthorid,
        :createddate,
        :modifieddate,
        :organizationid,
        :userintegrationid
    )
    RETURNING id, pullrequestid, repoid, organizationid
    """
)


class PrUpdateRepository:
    """Handles pr_update table inserts."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        if not rows:
            return []

        inserted: List[Dict] = []
        for row in rows:
            result = session.execute(PR_UPDATE_INSERT_SQL, row)
            inserted.append(dict(result.mappings().one()))

        return inserted

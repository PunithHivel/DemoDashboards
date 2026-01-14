from __future__ import annotations

from typing import Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

PR_REVIEWER_COLUMNS = [
    "pullrequestid",
    "authorid",
    "approved",
    "usertype",
    "comment",
    "accountid",
    "approveddate",
    "originalauthorid",
    "createddate",
    "modifieddate",
    "organizationid",
    "userintegrationid",
    "repoid",
]

PR_REVIEWER_INSERT_SQL = text(
    """
    INSERT INTO insightly.pr_reviewer (
        pullrequestid,
        authorid,
        approved,
        usertype,
        comment,
        accountid,
        approveddate,
        originalauthorid,
        createddate,
        modifieddate,
        organizationid,
        userintegrationid,
        repoid
    ) VALUES (
        :pullrequestid,
        :authorid,
        :approved,
        :usertype,
        :comment,
        :accountid,
        :approveddate,
        :originalauthorid,
        :createddate,
        :modifieddate,
        :organizationid,
        :userintegrationid,
        :repoid
    )
    RETURNING id, pullrequestid, authorid, organizationid
    """
)


class PrReviewerRepository:
    """Handles pr_reviewer table inserts."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        if not rows:
            return []

        inserted: List[Dict] = []
        for row in rows:
            result = session.execute(PR_REVIEWER_INSERT_SQL, row)
            inserted.append(dict(result.mappings().one()))

        return inserted

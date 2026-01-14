from __future__ import annotations

from typing import Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

PR_COMMENT_COLUMNS = [
    "commentid",
    "createdon",
    "deleted",
    "text",
    "updatedon",
    "authorid",
    "pullrequestid",
    "type",
    "originalauthorid",
    "createddate",
    "modifieddate",
    "organizationid",
    "threadid",
    "userintegrationid",
    "sentimentscore",
    "sentimentcomment",
    "sentimentprocessed",
]

PR_COMMENT_INSERT_SQL = text(
    """
    INSERT INTO insightly.pr_comment (
        commentid,
        createdon,
        deleted,
        text,
        updatedon,
        authorid,
        pullrequestid,
        type,
        originalauthorid,
        createddate,
        modifieddate,
        organizationid,
        threadid,
        userintegrationid,
        sentimentscore,
        sentimentcomment,
        sentimentprocessed
    ) VALUES (
        :commentid,
        :createdon,
        :deleted,
        :text,
        :updatedon,
        :authorid,
        :pullrequestid,
        :type,
        :originalauthorid,
        :createddate,
        :modifieddate,
        :organizationid,
        :threadid,
        :userintegrationid,
        :sentimentscore,
        :sentimentcomment,
        :sentimentprocessed
    )
    RETURNING id, pullrequestid, authorid, organizationid
    """
)


class PrCommentRepository:
    """Handles pr_comment table inserts."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        if not rows:
            return []

        inserted: List[Dict] = []
        for row in rows:
            result = session.execute(PR_COMMENT_INSERT_SQL, row)
            inserted.append(dict(result.mappings().one()))

        return inserted

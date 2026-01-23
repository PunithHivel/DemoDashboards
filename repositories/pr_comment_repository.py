from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from .bulk_copy import bulk_copy_insert

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


class PrCommentRepository:
    """Handles pr_comment table inserts using high-performance COPY."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        """
        Bulk insert PR comments using PostgreSQL COPY command.
        
        This is 10-100x faster than row-by-row inserts.
        Returns summary of inserted rows (not individual IDs due to COPY limitations).
        """
        if not rows:
            return []

        count = bulk_copy_insert(
            session=session,
            table_name="pr_comment",
            columns=PR_COMMENT_COLUMNS,
            rows=rows,
        )
        
        # Return summary since COPY doesn't support RETURNING
        return [{"inserted_count": count}]

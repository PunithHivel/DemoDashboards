from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from .bulk_copy import bulk_copy_upsert

COMMIT_COLUMNS = [
    "hash",
    "authorid",
    "commitid",
    "type",
    "date",
    "skippedregexfiles",
    "missingcommit",
    "message",
    "repoid",
    "createddate",
    "modifieddate",
    "repositoryuuid",
    "repositoryfullname",
    "htmllink",
    "rework",
    "newwork",
    "maintenance",
    "assistance",
    "linesadded",
    "linesremoved",
    "originalauthorid",
    "processed",
    "skipfromcalculation",
    "branch",
    "jiramappingprocessed",
    "organizationid",
    "workspaceid",
    "codingfilter",
    "userintegrationid",
    "jiradatacollected",
    "estimated_storypoints",
    "remark",
    "is_auto_excluded",
]

# Columns that form the unique constraint
COMMIT_CONFLICT_COLUMNS = ["hash", "repoid", "organizationid"]


class CommitRepository:
    """Handles commit table inserts using high-performance COPY."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        """
        Bulk insert/upsert commits using PostgreSQL COPY command.
        
        Uses temp table + COPY + INSERT ON CONFLICT for maximum performance.
        Returns summary of inserted rows (not individual IDs due to COPY limitations).
        """
        if not rows:
            return []

        count = bulk_copy_upsert(
            session=session,
            table_name="commit",
            columns=COMMIT_COLUMNS,
            rows=rows,
            conflict_columns=COMMIT_CONFLICT_COLUMNS,
        )
        
        # Return summary since COPY doesn't support RETURNING
        return [{"inserted_count": count}]

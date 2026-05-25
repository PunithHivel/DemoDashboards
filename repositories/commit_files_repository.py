from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from .bulk_copy import bulk_copy_insert

COMMIT_FILES_COLUMNS = [
    "commitid",
    "name",
    "repopathname",
    "status",
    "linesadded",
    "linesremoved",
    "newwork",
    "rework",
    "maintenance",
    "assistance",
    "createddate",
    "modifieddate",
    "skippedfromcalculation",
    "remark",
]


class CommitFilesRepository:
    """Handles commit_files table inserts using high-performance COPY."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        """
        Bulk insert commit files using PostgreSQL COPY command.
        
        This is 10-100x faster than row-by-row inserts.
        Returns summary of inserted rows (not individual IDs due to COPY limitations).
        """
        if not rows:
            return []

        count = bulk_copy_insert(
            session=session,
            table_name="commit_files",
            columns=COMMIT_FILES_COLUMNS,
            rows=rows,
        )
        
        # Return summary since COPY doesn't support RETURNING
        return [{"inserted_count": count}]

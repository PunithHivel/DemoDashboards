from __future__ import annotations

from typing import Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

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

COMMIT_FILES_INSERT_SQL = text(
    """
    INSERT INTO insightly.commit_files (
        commitid,
        name,
        repopathname,
        status,
        linesadded,
        linesremoved,
        newwork,
        rework,
        maintenance,
        assistance,
        createddate,
        modifieddate,
        skippedfromcalculation,
        remark
    ) VALUES (
        :commitid,
        :name,
        :repopathname,
        :status,
        :linesadded,
        :linesremoved,
        :newwork,
        :rework,
        :maintenance,
        :assistance,
        :createddate,
        :modifieddate,
        :skippedfromcalculation,
        :remark
    )
    RETURNING id, commitid, name, repopathname
    """
)


class CommitFilesRepository:
    """Handles commit_files table inserts."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        if not rows:
            return []

        inserted: List[Dict] = []
        for row in rows:
            result = session.execute(COMMIT_FILES_INSERT_SQL, row)
            inserted.append(dict(result.mappings().one()))

        return inserted

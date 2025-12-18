from __future__ import annotations

from typing import Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

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

COMMIT_INSERT_SQL = text(
    """
    INSERT INTO insightly.commit (
        hash,
        authorid,
        commitid,
        type,
        date,
        skippedregexfiles,
        missingcommit,
        message,
        repoid,
        createddate,
        modifieddate,
        repositoryuuid,
        repositoryfullname,
        htmllink,
        rework,
        newwork,
        maintenance,
        assistance,
        linesadded,
        linesremoved,
        originalauthorid,
        processed,
        skipfromcalculation,
        branch,
        jiramappingprocessed,
        organizationid,
        workspaceid,
        codingfilter,
        userintegrationid,
        jiradatacollected,
        estimated_storypoints,
        remark,
        is_auto_excluded
    ) VALUES (
        :hash,
        :authorid,
        :commitid,
        :type,
        :date,
        :skippedregexfiles,
        :missingcommit,
        :message,
        :repoid,
        :createddate,
        :modifieddate,
        :repositoryuuid,
        :repositoryfullname,
        :htmllink,
        :rework,
        :newwork,
        :maintenance,
        :assistance,
        :linesadded,
        :linesremoved,
        :originalauthorid,
        :processed,
        :skipfromcalculation,
        :branch,
        :jiramappingprocessed,
        :organizationid,
        :workspaceid,
        :codingfilter,
        :userintegrationid,
        :jiradatacollected,
        :estimated_storypoints,
        :remark,
        :is_auto_excluded
    )
    RETURNING id, hash, repoid, organizationid
    """
)


class CommitRepository:
    """Handles commit table inserts."""

    def bulk_insert(self, session: Session, rows: List[Dict]) -> List[Dict]:
        if not rows:
            return []

        inserted: List[Dict] = []
        for row in rows:
            result = session.execute(COMMIT_INSERT_SQL, row)
            inserted.append(dict(result.mappings().one()))

        return inserted

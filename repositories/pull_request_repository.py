from __future__ import annotations

from typing import Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from .bulk_copy import bulk_copy_upsert

PULL_REQUEST_COLUMNS = [
    "organizationid",
    "workspaceid",
    "actualpullrequestid",
    "title",
    "authorid",
    "createdon",
    "description",
    "destinationbranch",
    "sourcebranch",
    "firstcommitid",
    "sourcecommitid",
    "destinationcommitid",
    "state",
    "repoid",
    "linesadded",
    "linesremoved",
    "htmllink",
    "commentcount",
    "commitscount",
    "modifiedfilescount",
    "reason",
    "updatedon",
    "mergecommit",
    "mergedby",
    "firstreviewedby",
    "approvedby",
    "originalmergedby",
    "mergedon",
    "declinedon",
    "reviewedon",
    "approvedon",
    "firstcommittedon",
    "committoopenduration",
    "opentoreviewduration",
    "reviewedtoapprovedduration",
    "reviewedtomergedduration",
    "approvedtomergedduration",
    "reviewedtodeclineduration",
    "opentodeclineduration",
    "opentomergedduration",
    "cycletimeduration",
    "deploytimeduration",
    "cycletimeoverflow",
    "declinedby",
    "remark",
    "originalauthorid",
    "createddate",
    "modifieddate",
    "originalapprovedby",
    "originalfirstreviewedby",
    "originaldeclinedby",
    "processed",
    "hotfixpr",
    "reviewbranchpr",
    "releasebranchpr",
    "excludepr",
    "flashyreviewedpr",
    "jiramappingprocessed",
    "labels",
    "prsentiment",
    "issourcebranchdeleted",
    "userintegrationid",
    "jiradatacollected",
    "reviewcyclecount",
    "autoexcludepr",
    "opentofirstcommentduration",
    "firstcommenttoapproved",
    "estimated_storypoints",
    "comment_sentiment_count",
    "is_deployment_pr",
    "mergetodeployduration",
    "deployment_record_id",
    "incident_record_id",
    "is_incident_pr",
]

# Columns that form the unique constraint
PULL_REQUEST_CONFLICT_COLUMNS = ["actualpullrequestid", "repoid", "organizationid"]


class PullRequestRepository:
    """Handles persistence for pull request imports using high-performance COPY."""

    def bulk_upsert(
        self, session: Session, rows: Sequence[Mapping]
    ) -> int:
        """
        Bulk upsert pull requests using PostgreSQL COPY command.
        
        Uses temp table + COPY + INSERT ON CONFLICT for maximum performance.
        """
        if not rows:
            return 0

        # Convert Mapping to List[Dict] for bulk_copy_upsert
        rows_list = [dict(r) for r in rows]
        
        return bulk_copy_upsert(
            session=session,
            table_name="pull_request",
            columns=PULL_REQUEST_COLUMNS,
            rows=rows_list,
            conflict_columns=PULL_REQUEST_CONFLICT_COLUMNS,
        )

    def check_table_and_count_by_org(
        self, session: Session, organization_id: int
    ) -> tuple[bool, int]:
        """Check if pull_request table exists and count PRs for the organization."""
        try:
            count_query = text(
                "SELECT COUNT(*) as count FROM insightly.pull_request WHERE organizationid = :organization_id"
            )
            result = session.execute(count_query, {"organization_id": organization_id}).mappings().first()
            count = result.get("count", 0) if result else 0
            return True, count
        except Exception:
            # Table doesn't exist or other error
            return False, 0

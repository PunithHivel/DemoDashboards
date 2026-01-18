from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from metrics_editor.models import ChangePlan, MetricChangeRequest
from metrics_editor.storage import create_plan_id


def _month_bounds(month_value: str) -> Tuple[date, date]:
    try:
        parsed = date.fromisoformat(month_value)
        year = parsed.year
        month = parsed.month
    except ValueError:
        parts = month_value.split("-")
        if len(parts) < 2:
            raise ValueError("month must be YYYY-MM or YYYY-MM-DD")
        year, month = [int(part) for part in parts[:2]]

    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def _filter_clauses(scope) -> Tuple[str, Dict[str, Any]]:
    clauses = ["organizationid = :org_id"]
    params: Dict[str, Any] = {"org_id": scope.organization_id}
    if scope.repo_id is not None:
        clauses.append("repoid = :repo_id")
        params["repo_id"] = scope.repo_id
    if scope.author_ids:
        clauses.append("authorid = ANY(:author_ids)")
        params["author_ids"] = scope.author_ids
    return " AND ".join(clauses), params


def _select_pr_ids(
    session: Session,
    scope,
    date_field: str,
    start: date,
    end: date,
    extra_filters: List[str],
    limit: int,
    extra_params: Dict[str, Any] | None = None,
) -> List[int]:
    where_sql, params = _filter_clauses(scope)
    params.update({"start": start, "end": end, "limit": limit})
    if extra_params:
        params.update(extra_params)
    filters = [where_sql, f"{date_field} >= :start", f"{date_field} < :end"]
    filters.extend(extra_filters)
    query = f"SELECT id FROM insightly.pull_request WHERE {' AND '.join(filters)} ORDER BY {date_field}, id LIMIT :limit"
    rows = session.execute(text(query), params).fetchall()
    return [row[0] for row in rows]


def plan_shift_open_prs(session: Session, request: MetricChangeRequest) -> ChangePlan:
    source_month = request.options.get("source_month")
    target_month = request.options.get("target_month")
    count = int(request.options.get("count", 0))
    if not source_month or not target_month:
        raise ValueError("source_month and target_month are required")
    if count <= 0:
        raise ValueError("count must be > 0")

    source_start, source_end = _month_bounds(source_month)
    target_start, _ = _month_bounds(target_month)
    delta_days = (target_start - source_start).days
    ids = _select_pr_ids(
        session,
        request.scope,
        "createdon",
        source_start,
        source_end,
        ["state = 'OPEN'"],
        count,
    )

    if not ids:
        raise ValueError("No matching OPEN PRs found for the source month")

    summary = f"Shift {len(ids)} OPEN PRs from {source_month} to {target_month}"
    sql = [
        """
        UPDATE insightly.pull_request
        SET createdon = createdon + (INTERVAL '1 day' * :delta_days),
            updatedon = CASE WHEN updatedon IS NOT NULL THEN updatedon + (INTERVAL '1 day' * :delta_days) ELSE NULL END,
            createddate = createddate + (INTERVAL '1 day' * :delta_days),
            modifieddate = modifieddate + (INTERVAL '1 day' * :delta_days)
        WHERE id = ANY(:ids);
        """,
        """
        UPDATE insightly.pr_reviewer
        SET approveddate = CASE WHEN approveddate IS NOT NULL THEN approveddate + (INTERVAL '1 day' * :delta_days) ELSE NULL END,
            createddate = createddate + (INTERVAL '1 day' * :delta_days),
            modifieddate = modifieddate + (INTERVAL '1 day' * :delta_days)
        WHERE pullrequestid = ANY(:ids);
        """,
        """
        UPDATE insightly.pr_update
        SET date = date + (INTERVAL '1 day' * :delta_days),
            createddate = createddate + (INTERVAL '1 day' * :delta_days),
            modifieddate = modifieddate + (INTERVAL '1 day' * :delta_days)
        WHERE pullrequestid = ANY(:ids);
        """,
        """
        UPDATE insightly.pr_comment
        SET createdon = createdon + (INTERVAL '1 day' * :delta_days),
            createddate = createddate + (INTERVAL '1 day' * :delta_days),
            modifieddate = modifieddate + (INTERVAL '1 day' * :delta_days)
        WHERE pullrequestid = ANY(:ids);
        """,
    ]
    params = {"ids": ids, "delta_days": delta_days}

    return ChangePlan(
        plan_id=create_plan_id(),
        summary=summary,
        sql_statements=[s.strip() for s in sql],
        sql_params=[params] * len(sql),
        before_rows=[],
        expected={"shifted_prs": len(ids)},
    )


def plan_shift_merged_prs(session: Session, request: MetricChangeRequest) -> ChangePlan:
    source_month = request.options.get("source_month")
    target_month = request.options.get("target_month")
    count = int(request.options.get("count", 0))
    if not source_month or not target_month:
        raise ValueError("source_month and target_month are required")
    if count <= 0:
        raise ValueError("count must be > 0")

    source_start, source_end = _month_bounds(source_month)
    target_start, _ = _month_bounds(target_month)
    delta_days = (target_start - source_start).days

    ids = _select_pr_ids(
        session,
        request.scope,
        "mergedon",
        source_start,
        source_end,
        ["state = 'MERGED'"],
        count,
    )
    if not ids:
        raise ValueError("No matching MERGED PRs found for the source month")

    summary = f"Shift {len(ids)} MERGED PRs from {source_month} to {target_month}"
    sql = [
        """
        UPDATE insightly.pull_request
        SET mergedon = mergedon + (INTERVAL '1 day' * :delta_days),
            approvedon = CASE WHEN approvedon IS NOT NULL THEN approvedon + (INTERVAL '1 day' * :delta_days) ELSE NULL END,
            createdon = createdon + (INTERVAL '1 day' * :delta_days),
            firstcommittedon = CASE WHEN firstcommittedon IS NOT NULL THEN firstcommittedon + (INTERVAL '1 day' * :delta_days) ELSE NULL END,
            updatedon = CASE WHEN updatedon IS NOT NULL THEN updatedon + (INTERVAL '1 day' * :delta_days) ELSE NULL END,
            createddate = createddate + (INTERVAL '1 day' * :delta_days),
            modifieddate = modifieddate + (INTERVAL '1 day' * :delta_days)
        WHERE id = ANY(:ids);
        """,
        """
        UPDATE insightly.pr_update
        SET date = date + (INTERVAL '1 day' * :delta_days),
            createddate = createddate + (INTERVAL '1 day' * :delta_days),
            modifieddate = modifieddate + (INTERVAL '1 day' * :delta_days)
        WHERE pullrequestid = ANY(:ids);
        """,
        """
        UPDATE insightly.pr_reviewer
        SET approveddate = CASE WHEN approveddate IS NOT NULL THEN approveddate + (INTERVAL '1 day' * :delta_days) ELSE NULL END,
            createddate = createddate + (INTERVAL '1 day' * :delta_days),
            modifieddate = modifieddate + (INTERVAL '1 day' * :delta_days)
        WHERE pullrequestid = ANY(:ids);
        """,
        """
        UPDATE insightly.pr_comment
        SET createdon = createdon + (INTERVAL '1 day' * :delta_days),
            createddate = createddate + (INTERVAL '1 day' * :delta_days),
            modifieddate = modifieddate + (INTERVAL '1 day' * :delta_days)
        WHERE pullrequestid = ANY(:ids);
        """,
    ]
    params = {"ids": ids, "delta_days": delta_days}

    return ChangePlan(
        plan_id=create_plan_id(),
        summary=summary,
        sql_statements=[s.strip() for s in sql],
        sql_params=[params] * len(sql),
        before_rows=[],
        expected={"shifted_prs": len(ids)},
    )


def plan_set_reviewed(session: Session, request: MetricChangeRequest, reviewed: bool) -> ChangePlan:
    month_value = request.options.get("month")
    count = int(request.options.get("count", 0))
    review_minutes = int(request.options.get("review_minutes", 180))
    if not month_value:
        raise ValueError("month is required (YYYY-MM)")
    if count <= 0:
        raise ValueError("count must be > 0")

    start, end = _month_bounds(month_value)
    extra = ["state = 'MERGED'"]
    if reviewed:
        extra.append("approvedon IS NULL")
    else:
        extra.append("approvedon IS NOT NULL")

    ids = _select_pr_ids(
        session,
        request.scope,
        "mergedon",
        start,
        end,
        extra,
        count,
        extra_params={"threshold_lines": threshold_lines},
    )
    if not ids:
        raise ValueError("No matching PRs found for the requested review toggle")

    if reviewed:
        summary = f"Mark {len(ids)} PRs as reviewed in {month_value}"
        sql = [
            """
            UPDATE insightly.pull_request
            SET approvedon = createdon + (INTERVAL '1 minute' * :review_minutes),
                approvedby = authorid,
                opentoreviewduration = :review_minutes,
                reviewbranchpr = TRUE,
                reviewedtomergedduration = CASE
                    WHEN mergedon IS NOT NULL THEN GREATEST(EXTRACT(EPOCH FROM (mergedon - (createdon + (INTERVAL '1 minute' * :review_minutes)))) / 60, 0)
                    ELSE reviewedtomergedduration
                END,
                approvedtomergedduration = CASE
                    WHEN mergedon IS NOT NULL THEN GREATEST(EXTRACT(EPOCH FROM (mergedon - (createdon + (INTERVAL '1 minute' * :review_minutes)))) / 60, 0)
                    ELSE approvedtomergedduration
                END,
                opentomergedduration = NULL,
                deploytimeduration = CASE
                    WHEN mergedon IS NOT NULL THEN GREATEST(EXTRACT(EPOCH FROM (mergedon - (createdon + (INTERVAL '1 minute' * :review_minutes)))) / 60, 0)
                    ELSE deploytimeduration
                END,
                cycletimeduration = COALESCE(committoopenduration, 0)
                    + :review_minutes
                    + CASE
                        WHEN mergedon IS NOT NULL THEN GREATEST(EXTRACT(EPOCH FROM (mergedon - (createdon + (INTERVAL '1 minute' * :review_minutes)))) / 60, 0)
                        ELSE COALESCE(deploytimeduration, 0)
                      END
            WHERE id = ANY(:ids);
            """,
            """
            UPDATE insightly.pr_reviewer
            SET approved = TRUE,
                approveddate = (SELECT approvedon FROM insightly.pull_request WHERE id = pullrequestid)
            WHERE pullrequestid = ANY(:ids);
            """,
            """
            INSERT INTO insightly.pr_reviewer (organizationid, pullrequestid, authorid, approved, approveddate)
            SELECT pr.organizationid, pr.id, pr.authorid, TRUE, pr.approvedon
            FROM insightly.pull_request pr
            WHERE pr.id = ANY(:ids)
              AND NOT EXISTS (
                SELECT 1 FROM insightly.pr_reviewer prr WHERE prr.pullrequestid = pr.id
              );
            """,
        ]
    else:
        summary = f"Mark {len(ids)} PRs as unreviewed in {month_value}"
        sql = [
            """
            UPDATE insightly.pull_request
            SET approvedon = NULL,
                approvedby = NULL,
                opentoreviewduration = NULL,
                reviewbranchpr = TRUE,
                reviewedtomergedduration = NULL,
                approvedtomergedduration = NULL,
                opentomergedduration = CASE
                    WHEN mergedon IS NOT NULL THEN GREATEST(EXTRACT(EPOCH FROM (mergedon - createdon)) / 60, 0)
                    ELSE opentomergedduration
                END,
                deploytimeduration = CASE
                    WHEN mergedon IS NOT NULL THEN GREATEST(EXTRACT(EPOCH FROM (mergedon - createdon)) / 60, 0)
                    ELSE deploytimeduration
                END,
                cycletimeduration = COALESCE(committoopenduration, 0)
                    + CASE
                        WHEN mergedon IS NOT NULL THEN GREATEST(EXTRACT(EPOCH FROM (mergedon - createdon)) / 60, 0)
                        ELSE COALESCE(opentomergedduration, 0)
                      END
            WHERE id = ANY(:ids);
            """,
            """
            UPDATE insightly.pr_reviewer
            SET approved = FALSE,
                approveddate = NULL
            WHERE pullrequestid = ANY(:ids);
            """,
        ]

    params = {"ids": ids, "review_minutes": review_minutes}
    return ChangePlan(
        plan_id=create_plan_id(),
        summary=summary,
        sql_statements=[s.strip() for s in sql],
        sql_params=[params] * len(sql),
        before_rows=[],
        expected={"updated_prs": len(ids)},
    )


def plan_set_flashy(session: Session, request: MetricChangeRequest, flashy: bool) -> ChangePlan:
    month_value = request.options.get("month")
    count = int(request.options.get("count", 0))
    flashy_minutes = int(request.options.get("flashy_minutes", 5))
    size_threshold = int(request.options.get("size_threshold", 400))
    regular_minutes = int(request.options.get("regular_minutes", 180))
    if not month_value:
        raise ValueError("month is required (YYYY-MM)")
    if count <= 0:
        raise ValueError("count must be > 0")

    start, end = _month_bounds(month_value)
    extra = ["state = 'MERGED'", "approvedon IS NOT NULL", "reviewbranchpr = TRUE"]
    if flashy:
        extra.append(f"(linesadded + linesremoved) > {size_threshold}")
        extra.append(f"(opentoreviewduration IS NULL OR opentoreviewduration >= {flashy_minutes})")
    else:
        extra.append(f"(linesadded + linesremoved) > {size_threshold}")
        extra.append(f"opentoreviewduration < {flashy_minutes}")

    ids = _select_pr_ids(session, request.scope, "mergedon", start, end, extra, count)
    if not ids:
        raise ValueError("No matching PRs found for flashy toggle")

    summary = f"Set {len(ids)} PRs to {'flashy' if flashy else 'regular'} reviews in {month_value}"
    target_minutes = flashy_minutes if flashy else regular_minutes
    sql = [
        """
        UPDATE insightly.pull_request
        SET opentoreviewduration = :target_minutes,
            flashyreviewedpr = :flashy_value,
            reviewbranchpr = TRUE,
            approvedby = COALESCE(approvedby, authorid),
            approvedon = createdon + (INTERVAL '1 minute' * :target_minutes),
            reviewedtomergedduration = CASE
                WHEN mergedon IS NOT NULL THEN GREATEST(EXTRACT(EPOCH FROM (mergedon - (createdon + (INTERVAL '1 minute' * :target_minutes)))) / 60, 0)
                ELSE reviewedtomergedduration
            END,
            deploytimeduration = CASE
                WHEN mergedon IS NOT NULL THEN GREATEST(EXTRACT(EPOCH FROM (mergedon - (createdon + (INTERVAL '1 minute' * :target_minutes)))) / 60, 0)
                ELSE deploytimeduration
            END,
            cycletimeduration = COALESCE(committoopenduration, 0)
                + :target_minutes
                + CASE
                    WHEN mergedon IS NOT NULL THEN GREATEST(EXTRACT(EPOCH FROM (mergedon - (createdon + (INTERVAL '1 minute' * :target_minutes)))) / 60, 0)
                    ELSE COALESCE(deploytimeduration, 0)
                  END
        WHERE id = ANY(:ids);
        """,
    ]
    params = {"ids": ids, "target_minutes": target_minutes, "flashy_value": flashy}
    return ChangePlan(
        plan_id=create_plan_id(),
        summary=summary,
        sql_statements=[s.strip() for s in sql],
        sql_params=[params],
        before_rows=[],
        expected={"updated_prs": len(ids)},
    )


def plan_toggle_flag(session: Session, request: MetricChangeRequest, column: str, value: bool) -> ChangePlan:
    month_value = request.options.get("month")
    count = int(request.options.get("count", 0))
    if not month_value:
        raise ValueError("month is required (YYYY-MM)")
    if count <= 0:
        raise ValueError("count must be > 0")

    start, end = _month_bounds(month_value)
    extra = ["state = 'MERGED'", f"{column} IS DISTINCT FROM :target_value"]
    ids = _select_pr_ids(session, request.scope, "mergedon", start, end, extra, count)
    if not ids:
        raise ValueError("No matching PRs found for flag toggle")

    summary = f"Set {column}={value} for {len(ids)} PRs in {month_value}"
    sql = [
        f"""
        UPDATE insightly.pull_request
        SET {column} = :target_value{', reviewbranchpr = TRUE' if column == 'releasebranchpr' and value else ''}
        WHERE id = ANY(:ids);
        """,
    ]
    params = {"ids": ids, "target_value": value}
    return ChangePlan(
        plan_id=create_plan_id(),
        summary=summary,
        sql_statements=[s.strip() for s in sql],
        sql_params=[params],
        before_rows=[],
        expected={"updated_prs": len(ids)},
    )


def plan_set_large_prs(session: Session, request: MetricChangeRequest, make_large: bool) -> ChangePlan:
    month_value = request.options.get("month")
    count = int(request.options.get("count", 0))
    if not month_value:
        raise ValueError("month is required (YYYY-MM)")
    if count <= 0:
        raise ValueError("count must be > 0")

    start, end = _month_bounds(month_value)
    threshold_lines = int(request.options.get("threshold_lines", 400))
    if make_large:
        extra = [
            "state = 'MERGED'",
            "(COALESCE(linesadded, 0) + COALESCE(linesremoved, 0)) <= :threshold_lines",
        ]
    else:
        extra = [
            "state = 'MERGED'",
            "(COALESCE(linesadded, 0) + COALESCE(linesremoved, 0)) > :threshold_lines",
        ]

    ids = _select_pr_ids(session, request.scope, "mergedon", start, end, extra, count)
    if not ids:
        raise ValueError("No matching PRs found for large PR toggle")

    target_lines = int(request.options.get("target_lines", 500 if make_large else 300))
    added_ratio = float(request.options.get("added_ratio", 0.6))
    added_ratio = min(max(added_ratio, 0.0), 1.0)
    lines_added = round(target_lines * added_ratio)
    lines_removed = max(target_lines - lines_added, 0)
    summary = f"Set {len(ids)} PRs to {'large' if make_large else 'small'} in {month_value}"

    sql = [
        """
        UPDATE insightly.pull_request
        SET linesadded = :lines_added,
            linesremoved = :lines_removed
        WHERE id = ANY(:ids);
        """,
    ]
    params = {
        "ids": ids,
        "lines_added": lines_added,
        "lines_removed": lines_removed,
        "threshold_lines": threshold_lines,
    }
    return ChangePlan(
        plan_id=create_plan_id(),
        summary=summary,
        sql_statements=[s.strip() for s in sql],
        sql_params=[params],
        before_rows=[],
        expected={"updated_prs": len(ids)},
    )


def plan_scale_duration(session: Session, request: MetricChangeRequest, column: str) -> ChangePlan:
    month_value = request.options.get("month")
    scale = float(request.options.get("scale", 1.0))
    if not month_value:
        raise ValueError("month is required (YYYY-MM)")
    if scale <= 0:
        raise ValueError("scale must be > 0")

    start, end = _month_bounds(month_value)
    ids = _select_pr_ids(
        session,
        request.scope,
        "mergedon",
        start,
        end,
        ["state = 'MERGED'"],
        limit=100000,
    )
    if not ids:
        raise ValueError("No matching PRs found for duration scaling")

    summary = f"Scale {column} by {scale} for {len(ids)} PRs in {month_value}"
    if column == "opentoreviewduration":
        sql = [
            """
            UPDATE insightly.pull_request
            SET opentoreviewduration = ROUND(COALESCE(opentoreviewduration, 0) * :scale),
                cycletimeduration = COALESCE(committoopenduration, 0)
                    + ROUND(COALESCE(opentoreviewduration, 0) * :scale)
                    + COALESCE(deploytimeduration, 0)
            WHERE id = ANY(:ids);
            """,
        ]
    elif column == "deploytimeduration":
        sql = [
            """
            UPDATE insightly.pull_request
            SET deploytimeduration = ROUND(COALESCE(deploytimeduration, 0) * :scale),
                cycletimeduration = COALESCE(committoopenduration, 0)
                    + COALESCE(opentoreviewduration, 0)
                    + ROUND(COALESCE(deploytimeduration, 0) * :scale)
            WHERE id = ANY(:ids);
            """,
        ]
    elif column == "committoopenduration":
        sql = [
            """
            UPDATE insightly.pull_request
            SET committoopenduration = ROUND(COALESCE(committoopenduration, 0) * :scale),
                cycletimeduration = ROUND(COALESCE(committoopenduration, 0) * :scale)
                    + COALESCE(opentoreviewduration, 0)
                    + COALESCE(deploytimeduration, 0)
            WHERE id = ANY(:ids);
            """,
        ]
    else:
        sql = [
            f"""
            UPDATE insightly.pull_request
            SET {column} = ROUND(COALESCE({column}, 0) * :scale)
            WHERE id = ANY(:ids);
            """,
        ]
    params = {"ids": ids, "scale": scale}
    return ChangePlan(
        plan_id=create_plan_id(),
        summary=summary,
        sql_statements=[s.strip() for s in sql],
        sql_params=[params],
        before_rows=[],
        expected={"updated_prs": len(ids)},
    )

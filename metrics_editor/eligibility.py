from __future__ import annotations

from typing import Any, Dict, List, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from metrics_editor.models import (
    EligibilityRequest,
    EligibilityResponse,
    EligibilitySummaryPoint,
    EligibilitySummaryRequest,
    EligibilitySummaryResponse,
    EligibleEntity,
)


PR_METRICS = {
    "pr_opened",
    "pr_merged",
    "pr_reviewed",
    "pr_unreviewed",
    "flashy_reviews",
    "large_prs",
    "review_time",
    "cycle_time",
    "delivery_lead_time",
    "deploy_time",
    "coding_time",
    "release_prs",
    "deployment_frequency",
    "hotfix_prs",
    "mttr",
}

COMMIT_METRICS = {"rework_pct", "newwork_pct", "maintenance_pct", "commit_frequency"}
CHANGE_METRICS: set[str] = set()


def _summary_definition(action: str, options: Dict[str, Any]) -> Tuple[str, str, str]:
    if action == "shift_open_prs":
        return "insightly.pull_request", "createdon", "state = 'OPEN'"
    if action == "shift_merged_prs":
        return "insightly.pull_request", "mergedon", "state = 'MERGED'"
    if action == "set_reviewed_count":
        return "insightly.pull_request", "mergedon", "state = 'MERGED' AND approvedon IS NULL"
    if action == "set_unreviewed_count":
        return "insightly.pull_request", "mergedon", "state = 'MERGED' AND approvedon IS NOT NULL"
    if action == "set_flashy_reviews":
        flashy = bool(options.get("flashy", True))
        size_threshold = int(options.get("size_threshold", 400))
        flashy_minutes = int(options.get("flashy_minutes", 5))
        if flashy:
            filter_sql = (
                "state = 'MERGED' AND approvedon IS NOT NULL AND reviewbranchpr = TRUE "
                f"AND (COALESCE(linesadded,0) + COALESCE(linesremoved,0)) > {size_threshold} "
                f"AND (opentoreviewduration IS NULL OR opentoreviewduration >= {flashy_minutes})"
            )
        else:
            filter_sql = (
                "state = 'MERGED' AND approvedon IS NOT NULL AND reviewbranchpr = TRUE "
                f"AND (COALESCE(linesadded,0) + COALESCE(linesremoved,0)) > {size_threshold} "
                f"AND opentoreviewduration < {flashy_minutes}"
            )
        return "insightly.pull_request", "mergedon", filter_sql
    if action in {"toggle_release_prs", "toggle_hotfix_prs"}:
        column = "releasebranchpr" if action == "toggle_release_prs" else "hotfixpr"
        target = bool(options.get("value", True))
        flag = "TRUE" if target else "FALSE"
        return "insightly.pull_request", "mergedon", f"state = 'MERGED' AND {column} IS DISTINCT FROM {flag}"
    if action == "set_large_prs":
        make_large = bool(options.get("large", True))
        threshold_lines = int(options.get("threshold_lines", 400))
        if make_large:
            filter_sql = (
                "state = 'MERGED' AND (COALESCE(linesadded,0) + COALESCE(linesremoved,0)) <= "
                f"{threshold_lines}"
            )
        else:
            filter_sql = (
                "state = 'MERGED' AND (COALESCE(linesadded,0) + COALESCE(linesremoved,0)) > "
                f"{threshold_lines}"
            )
        return "insightly.pull_request", "mergedon", filter_sql
    if action in {"scale_review_time", "scale_cycle_time", "scale_deploy_time", "scale_coding_time", "scale_mttr_duration"}:
        return "insightly.pull_request", "mergedon", "state = 'MERGED'"
    if action in {"set_commit_mix", "shift_commit_dates"}:
        return "insightly.commit", "date", "type = 'COMMIT'"
    return "insightly.pull_request", "mergedon", "state = 'MERGED'"


def _pr_filter(metric_id: str) -> Tuple[str, str]:
    if metric_id == "pr_opened":
        return "createdon", "state IN ('OPEN', 'MERGED', 'DECLINED')"
    if metric_id == "pr_merged":
        return "mergedon", "state = 'MERGED'"
    if metric_id == "pr_reviewed":
        return (
            "mergedon",
            "state = 'MERGED' AND approvedon IS NOT NULL AND reviewbranchpr = TRUE "
            "AND autoexcludepr = FALSE AND excludepr = FALSE",
        )
    if metric_id == "pr_unreviewed":
        return (
            "mergedon",
            "state = 'MERGED' AND approvedon IS NULL AND reviewbranchpr = TRUE "
            "AND autoexcludepr = FALSE AND excludepr = FALSE",
        )
    if metric_id == "flashy_reviews":
        return (
            "mergedon",
            "state = 'MERGED' AND reviewbranchpr = TRUE AND approvedby IS NOT NULL "
            "AND opentoreviewduration IS NOT NULL AND opentoreviewduration < 5 "
            "AND (COALESCE(linesadded, 0) + COALESCE(linesremoved, 0)) > 400",
        )
    if metric_id == "large_prs":
        return (
            "mergedon",
            "state = 'MERGED' AND (COALESCE(linesadded, 0) + COALESCE(linesremoved, 0)) > 400",
        )
    if metric_id in {"review_time", "cycle_time", "deploy_time", "coding_time"}:
        return "mergedon", "state = 'MERGED'"
    if metric_id == "delivery_lead_time":
        return (
            "mergedon",
            "state = 'MERGED' AND cycletimeduration IS NOT NULL AND mergetodeployduration IS NOT NULL",
        )
    if metric_id == "release_prs":
        return "mergedon", "state = 'MERGED' AND releasebranchpr = TRUE"
    if metric_id == "deployment_frequency":
        return "mergedon", "state = 'MERGED'"
    if metric_id == "hotfix_prs":
        return "mergedon", "state = 'MERGED' AND hotfixpr = TRUE"
    if metric_id == "mttr":
        return "mergedon", "state = 'MERGED' AND hotfixpr = TRUE AND cycletimeduration IS NOT NULL"
    return "mergedon", "state = 'MERGED'"


def _commit_filter() -> Tuple[str, str]:
    return "date", "type = 'COMMIT'"


def _change_filter() -> Tuple[str, str]:
    return "start_date", "organization_id IS NOT NULL"


def get_eligible_entities(session: Session, request: EligibilityRequest) -> EligibilityResponse:
    if request.metric_id in PR_METRICS:
        date_field, filter_sql = _pr_filter(request.metric_id)
        table = "insightly.pull_request"
        org_column = "organizationid"
        repo_column = "repoid"
        author_column = "authorid"
        team_join = True
    elif request.metric_id in COMMIT_METRICS:
        date_field, filter_sql = _commit_filter()
        table = "insightly.commit"
        org_column = "organizationid"
        repo_column = "repoid"
        author_column = "authorid"
        team_join = True
    elif request.metric_id in CHANGE_METRICS:
        date_field, filter_sql = _change_filter()
        table = "insightly.change_requests"
        org_column = "organization_id"
        repo_column = "repoid"
        author_column = "authorid"
        team_join = False
    else:
        return EligibilityResponse(metric_id=request.metric_id)

    params: Dict[str, Any] = {
        "org_id": request.organization_id,
        "start": request.start_date,
        "end": request.end_date,
    }
    filters = [f"{org_column} = :org_id", filter_sql, f"{date_field} >= :start", f"{date_field} < :end"]
    if request.repo_id is not None:
        filters.append(f"{repo_column} = :repo_id")
        params["repo_id"] = request.repo_id
    if request.author_ids:
        filters.append(f"{author_column} = ANY(:author_ids)")
        params["author_ids"] = request.author_ids
    if request.team_id is not None:
        params["team_id"] = request.team_id
        if team_join:
            filters.append(
                f"{author_column} IN ("
                f"SELECT tar.authorid FROM insightly.teamauthorrelation tar "
                f"WHERE tar.organizationid = :org_id AND tar.teamid = :team_id "
                f"AND (tar.exitdate IS NULL OR tar.exitdate > NOW())"
                f")"
            )
        else:
            filters.append("team_id = :team_id")

    where_sql = " AND ".join(filters)

    author_query = f"""
        SELECT {"t." if team_join and request.team_id is not None else ""}{author_column} AS id, COUNT(*) AS count
        FROM {table}{"" if not (team_join and request.team_id is not None) else " t"}
        {"JOIN insightly.teamauthorrelation tar ON tar.organizationid = t." + org_column + " AND tar.authorid = t." + author_column if team_join and request.team_id is not None else ""}
        WHERE {"t." if team_join and request.team_id is not None else ""}{org_column} = :org_id AND {filter_sql} AND {"t." if team_join and request.team_id is not None else ""}{date_field} >= :start AND {"t." if team_join and request.team_id is not None else ""}{date_field} < :end
          {"AND tar.teamid = :team_id" if team_join and request.team_id is not None else ""}
          {"AND " + ("t." if team_join and request.team_id is not None else "") + repo_column + " = :repo_id" if request.repo_id is not None else ""}
          {"AND " + ("t." if team_join and request.team_id is not None else "") + author_column + " = ANY(:author_ids)" if request.author_ids else ""}
          AND {"t." if team_join and request.team_id is not None else ""}{author_column} IS NOT NULL
        GROUP BY {"t." if team_join and request.team_id is not None else ""}{author_column}
        ORDER BY COUNT(*) DESC
    """
    author_rows = session.execute(text(author_query), params).mappings().all()
    authors = [EligibleEntity(id=row["id"], count=row["count"]) for row in author_rows]

    repo_query = f"""
        SELECT {repo_column} AS id, COUNT(*) AS count
        FROM {table}
        WHERE {where_sql}
          AND {repo_column} IS NOT NULL
        GROUP BY {repo_column}
        ORDER BY COUNT(*) DESC
    """
    repo_rows = session.execute(text(repo_query), params).mappings().all()
    repos = [EligibleEntity(id=row["id"], count=row["count"]) for row in repo_rows]

    teams: List[EligibleEntity] = []
    if team_join:
        team_query = f"""
            SELECT tar.teamid AS id, COUNT(*) AS count
            FROM {table} t
            JOIN insightly.teamauthorrelation tar
              ON tar.organizationid = t.{org_column}
             AND tar.authorid = t.{author_column}
            WHERE t.{org_column} = :org_id AND {filter_sql} AND t.{date_field} >= :start AND t.{date_field} < :end
            {"AND tar.teamid = :team_id" if request.team_id is not None else ""}
            {"AND t." + repo_column + " = :repo_id" if request.repo_id is not None else ""}
            {"AND t." + author_column + " = ANY(:author_ids)" if request.author_ids else ""}
            GROUP BY tar.teamid
            ORDER BY COUNT(*) DESC
        """
        team_rows = session.execute(text(team_query), params).mappings().all()
        teams = [EligibleEntity(id=row["id"], count=row["count"]) for row in team_rows]
    else:
        team_query = f"""
            SELECT team_id AS id, COUNT(*) AS count
            FROM {table}
            WHERE {where_sql}
              {"AND team_id = :team_id" if request.team_id is not None else ""}
              AND team_id IS NOT NULL
            GROUP BY team_id
            ORDER BY COUNT(*) DESC
        """
        team_rows = session.execute(text(team_query), params).mappings().all()
        teams = [EligibleEntity(id=row["id"], count=row["count"]) for row in team_rows]

    return EligibilityResponse(metric_id=request.metric_id, repos=repos, teams=teams, authors=authors)


def get_eligible_summary(session: Session, request: EligibilitySummaryRequest) -> EligibilitySummaryResponse:
    table, date_field, filter_sql = _summary_definition(request.action, request.options)
    scope = request.scope
    params: Dict[str, Any] = {
        "org_id": scope.organization_id,
        "start": scope.start_date,
        "end": scope.end_date,
    }

    filters = ["organizationid = :org_id", filter_sql, f"{date_field} >= :start", f"{date_field} < :end"]
    if scope.repo_id is not None:
        filters.append("repoid = :repo_id")
        params["repo_id"] = scope.repo_id
    if scope.author_ids:
        filters.append("authorid = ANY(:author_ids)")
        params["author_ids"] = scope.author_ids

    query = f"""
        SELECT DATE_TRUNC('month', {date_field}) AS period,
               COUNT(*) AS eligible_count
        FROM {table}
        WHERE {' AND '.join(filters)}
        GROUP BY DATE_TRUNC('month', {date_field})
        ORDER BY DATE_TRUNC('month', {date_field})
    """
    rows = session.execute(text(query), params).fetchall()
    points = [
        EligibilitySummaryPoint(period=row[0].strftime("%Y-%m"), eligible_count=int(row[1] or 0))
        for row in rows
    ]
    return EligibilitySummaryResponse(metric_id=request.metric_id, action=request.action, by_period=points)

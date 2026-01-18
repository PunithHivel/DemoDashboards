from __future__ import annotations

from typing import Any, Dict, List, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from metrics_editor.models import EligibilityRequest, EligibilityResponse, EligibleEntity


PR_METRICS = {
    "pr_opened",
    "pr_merged",
    "pr_reviewed",
    "pr_unreviewed",
    "flashy_reviews",
    "large_prs",
    "review_time",
    "cycle_time",
    "deploy_time",
    "coding_time",
    "release_prs",
    "hotfix_prs",
}

COMMIT_METRICS = {"rework_pct", "newwork_pct", "maintenance_pct", "commit_frequency"}
CHANGE_METRICS = {"mttr"}


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
    if metric_id == "release_prs":
        return "mergedon", "state = 'MERGED' AND releasebranchpr = TRUE"
    if metric_id == "hotfix_prs":
        return "mergedon", "state = 'MERGED' AND hotfixpr = TRUE"
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

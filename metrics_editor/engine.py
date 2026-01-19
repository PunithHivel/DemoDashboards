from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from metrics_editor.catalog import get_metric, load_catalog
from metrics_editor.models import ChangePlan, MetricChangeRequest, MetricPoint, MetricSnapshot
from metrics_editor.playbooks.commit_metrics import plan_set_commit_mix, plan_shift_commit_dates
from metrics_editor.playbooks.change_requests import plan_scale_mttr
from metrics_editor.playbooks.pr_metrics import (
    plan_scale_duration,
    plan_set_flashy,
    plan_set_large_prs,
    plan_set_reviewed,
    plan_shift_merged_prs,
    plan_shift_open_prs,
    plan_toggle_flag,
)


def build_plan(session: Session, request: MetricChangeRequest) -> ChangePlan:
    action = request.action
    if action == "shift_open_prs":
        return plan_shift_open_prs(session, request)
    if action == "shift_merged_prs":
        return plan_shift_merged_prs(session, request)
    if action == "set_reviewed_count":
        return plan_set_reviewed(session, request, reviewed=True)
    if action == "set_unreviewed_count":
        return plan_set_reviewed(session, request, reviewed=False)
    if action == "set_flashy_reviews":
        flashy = bool(request.options.get("flashy", True))
        return plan_set_flashy(session, request, flashy=flashy)
    if action == "toggle_release_prs":
        target = bool(request.options.get("value", True))
        return plan_toggle_flag(session, request, "releasebranchpr", target)
    if action == "toggle_hotfix_prs":
        target = bool(request.options.get("value", True))
        return plan_toggle_flag(session, request, "hotfixpr", target)
    if action == "set_large_prs":
        make_large = bool(request.options.get("large", True))
        return plan_set_large_prs(session, request, make_large)
    if action == "scale_review_time":
        return plan_scale_duration(session, request, "opentoreviewduration")
    if action == "scale_cycle_time":
        return plan_scale_duration(session, request, "cycletimeduration")
    if action == "scale_deploy_time":
        return plan_scale_duration(session, request, "deploytimeduration")
    if action == "scale_coding_time":
        return plan_scale_duration(session, request, "committoopenduration")
    if action == "scale_mttr_duration":
        return plan_scale_mttr(session, request)
    if action == "set_commit_mix":
        return plan_set_commit_mix(session, request)
    if action == "shift_commit_dates":
        return plan_shift_commit_dates(session, request)
    raise ValueError(f"Unsupported action: {action}")


def get_affected_metric_ids(metric_id: str) -> List[str]:
    catalog = load_catalog()
    metric = get_metric(catalog, metric_id)
    if not metric:
        return [metric_id]
    affects = metric.get("affects") or []
    return list(dict.fromkeys([metric_id, *affects]))


def preview_impact(session: Session, request: MetricChangeRequest) -> Dict[str, MetricSnapshot]:
    affected = get_affected_metric_ids(request.metric_id)
    snapshots: Dict[str, MetricSnapshot] = {}
    for metric_id in affected:
        snapshots[metric_id] = snapshot_metric(session, metric_id, request.scope)

    return snapshots


def preview_after(session: Session, request: MetricChangeRequest, plan: ChangePlan) -> Dict[str, MetricSnapshot]:
    affected = get_affected_metric_ids(request.metric_id)
    snapshots: Dict[str, MetricSnapshot] = {}
    transaction = session.begin_nested()
    try:
        for statement, params in zip(plan.sql_statements, plan.sql_params):
            session.execute(text(statement), params)
        for metric_id in affected:
            snapshots[metric_id] = snapshot_metric(session, metric_id, request.scope)
    finally:
        transaction.rollback()
        session.expire_all()
    return snapshots


def _filter_clauses(scope) -> Dict[str, Any]:
    clauses = ["organizationid = :org_id"]
    params: Dict[str, Any] = {"org_id": scope.organization_id}
    if scope.repo_id is not None:
        clauses.append("repoid = :repo_id")
        params["repo_id"] = scope.repo_id
    if scope.author_ids:
        clauses.append("authorid = ANY(:author_ids)")
        params["author_ids"] = scope.author_ids
    return {"sql": " AND ".join(clauses), "params": params}


def snapshot_metric(session: Session, metric_id: str, scope) -> MetricSnapshot:
    base = _filter_clauses(scope)
    params = dict(base["params"])
    params.update({"start": scope.start_date, "end": scope.end_date})

    if metric_id in {
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
    }:
        return _snapshot_pr_metrics(session, metric_id, scope, base["sql"], params)

    if metric_id in {"rework_pct", "newwork_pct", "maintenance_pct", "commit_frequency"}:
        return _snapshot_commit_metrics(session, metric_id, scope, base["sql"], params)

    return MetricSnapshot(metric_id=metric_id, scope=scope, total_value=0, by_period=[])


def _snapshot_pr_metrics(session: Session, metric_id: str, scope, where_sql: str, params: Dict[str, Any]) -> MetricSnapshot:
    if metric_id == "pr_opened":
        date_field = "createdon"
        filter_sql = "state IN ('OPEN', 'MERGED', 'DECLINED')"
        value_expr = "COUNT(*)"
    elif metric_id == "pr_merged":
        date_field = "mergedon"
        filter_sql = "state = 'MERGED'"
        value_expr = "COUNT(*)"
    elif metric_id == "pr_reviewed":
        date_field = "mergedon"
        filter_sql = (
            "state = 'MERGED' AND approvedon IS NOT NULL AND reviewbranchpr = TRUE "
            "AND autoexcludepr = FALSE AND excludepr = FALSE"
        )
        value_expr = "COUNT(*)"
    elif metric_id == "pr_unreviewed":
        date_field = "mergedon"
        filter_sql = (
            "state = 'MERGED' AND approvedon IS NULL AND reviewbranchpr = TRUE "
            "AND autoexcludepr = FALSE AND excludepr = FALSE"
        )
        value_expr = "COUNT(*)"
    elif metric_id == "flashy_reviews":
        date_field = "mergedon"
        filter_sql = (
            "state = 'MERGED' AND reviewbranchpr = TRUE AND approvedby IS NOT NULL "
            "AND opentoreviewduration IS NOT NULL AND opentoreviewduration < 5 "
            "AND (COALESCE(linesadded, 0) + COALESCE(linesremoved, 0)) > 400"
        )
        value_expr = "COUNT(*)"
    elif metric_id == "large_prs":
        date_field = "mergedon"
        filter_sql = "state = 'MERGED' AND (COALESCE(linesadded, 0) + COALESCE(linesremoved, 0)) > 400"
        value_expr = "COUNT(*)"
    elif metric_id == "review_time":
        date_field = "mergedon"
        filter_sql = "state = 'MERGED'"
        value_expr = "AVG(opentoreviewduration)"
    elif metric_id == "cycle_time":
        date_field = "mergedon"
        filter_sql = "state = 'MERGED'"
        value_expr = "AVG(cycletimeduration)"
    elif metric_id == "delivery_lead_time":
        date_field = "mergedon"
        filter_sql = "state = 'MERGED' AND cycletimeduration IS NOT NULL AND mergetodeployduration IS NOT NULL"
        value_expr = "AVG(cycletimeduration + mergetodeployduration)"
    elif metric_id == "deploy_time":
        date_field = "mergedon"
        filter_sql = "state = 'MERGED'"
        value_expr = "AVG(deploytimeduration)"
    elif metric_id == "coding_time":
        date_field = "mergedon"
        filter_sql = "state = 'MERGED'"
        value_expr = "AVG(committoopenduration)"
    elif metric_id == "release_prs":
        date_field = "mergedon"
        filter_sql = "state = 'MERGED' AND releasebranchpr = TRUE"
        value_expr = "COUNT(*)"
    elif metric_id == "deployment_frequency":
        date_field = "mergedon"
        filter_sql = "state = 'MERGED'"
        value_expr = (
            "CASE WHEN COUNT(*) = 0 THEN 0 "
            "ELSE SUM(CASE WHEN releasebranchpr = TRUE THEN 1 ELSE 0 END)::numeric / COUNT(*) END"
        )
    elif metric_id == "hotfix_prs":
        date_field = "mergedon"
        filter_sql = "state = 'MERGED' AND hotfixpr = TRUE"
        value_expr = "COUNT(*)"
    elif metric_id == "mttr":
        date_field = "mergedon"
        filter_sql = "state = 'MERGED' AND hotfixpr = TRUE AND cycletimeduration IS NOT NULL"
        value_expr = "AVG(cycletimeduration)"
    else:
        return MetricSnapshot(metric_id=metric_id, scope=scope, total_value=0, by_period=[])

    query = f"""
        SELECT DATE_TRUNC('month', {date_field}) AS period,
               {value_expr}::numeric AS value
        FROM insightly.pull_request
        WHERE {where_sql}
          AND {filter_sql}
          AND {date_field} >= :start AND {date_field} < :end
        GROUP BY DATE_TRUNC('month', {date_field})
        ORDER BY DATE_TRUNC('month', {date_field})
    """
    rows = session.execute(text(query), params).fetchall()
    points = [MetricPoint(period=row[0].strftime("%Y-%m"), value=float(row[1] or 0)) for row in rows]
    total_value = sum(point.value for point in points)
    return MetricSnapshot(metric_id=metric_id, scope=scope, total_value=total_value, by_period=points)


def _snapshot_commit_metrics(session: Session, metric_id: str, scope, where_sql: str, params: Dict[str, Any]) -> MetricSnapshot:
    if metric_id == "commit_frequency":
        query = f"""
            SELECT DATE_TRUNC('month', date) AS period,
                   COUNT(*)::numeric AS value
            FROM insightly.commit
            WHERE {where_sql}
              AND type = 'COMMIT'
              AND date >= :start AND date < :end
            GROUP BY DATE_TRUNC('month', date)
            ORDER BY DATE_TRUNC('month', date)
        """
        rows = session.execute(text(query), params).fetchall()
        points = [MetricPoint(period=row[0].strftime("%Y-%m"), value=float(row[1] or 0)) for row in rows]
        total_value = sum(point.value for point in points)
        return MetricSnapshot(metric_id=metric_id, scope=scope, total_value=total_value, by_period=points)

    if metric_id in {"rework_pct", "newwork_pct", "maintenance_pct"}:
        if metric_id == "rework_pct":
            numerator = "SUM(rework + assistance)"
        elif metric_id == "newwork_pct":
            numerator = "SUM(newwork)"
        else:
            numerator = "SUM(maintenance)"

        query = f"""
            SELECT DATE_TRUNC('month', date) AS period,
                   CASE WHEN SUM(newwork + rework + assistance + maintenance) = 0 THEN 0
                        ELSE ({numerator}) * 100.0 / SUM(newwork + rework + assistance + maintenance)
                   END AS value
            FROM insightly.commit
            WHERE {where_sql}
              AND type = 'COMMIT'
              AND date >= :start AND date < :end
            GROUP BY DATE_TRUNC('month', date)
            ORDER BY DATE_TRUNC('month', date)
        """
        rows = session.execute(text(query), params).fetchall()
        points = [MetricPoint(period=row[0].strftime("%Y-%m"), value=float(row[1] or 0)) for row in rows]
        total_value = sum(point.value for point in points)
        return MetricSnapshot(metric_id=metric_id, scope=scope, total_value=total_value, by_period=points)

    return MetricSnapshot(metric_id=metric_id, scope=scope, total_value=0, by_period=[])


def _snapshot_change_metrics(session: Session, scope) -> MetricSnapshot:
    params: Dict[str, Any] = {
        "org_id": scope.organization_id,
        "start": scope.start_date,
        "end": scope.end_date,
    }
    filters = ["organization_id = :org_id"]
    if scope.repo_id is not None:
        filters.append("repoid = :repo_id")
        params["repo_id"] = scope.repo_id
    if scope.author_ids:
        filters.append("authorid = ANY(:author_ids)")
        params["author_ids"] = scope.author_ids

    query = f"""
        SELECT DATE_TRUNC('month', start_date) AS period,
               COUNT(*) AS totalcount,
               COALESCE(SUM(duration), 0) AS totalmetriccount
        FROM insightly.change_requests
        WHERE {' AND '.join(filters)}
          AND start_date >= :start AND start_date < :end
        GROUP BY DATE_TRUNC('month', start_date)
        ORDER BY DATE_TRUNC('month', start_date)
    """
    rows = session.execute(text(query), params).fetchall()

    points: List[MetricPoint] = []
    total_sum = 0.0
    total_count = 0.0
    for row in rows:
        period, count, total = row
        count_val = float(count or 0)
        total_val = float(total or 0)
        avg_val = 0.0 if count_val == 0 else total_val / count_val
        points.append(MetricPoint(period=period.strftime("%Y-%m"), value=avg_val))
        total_sum += total_val
        total_count += count_val

    overall_avg = 0.0 if total_count == 0 else total_sum / total_count
    return MetricSnapshot(metric_id="mttr", scope=scope, total_value=overall_avg, by_period=points)

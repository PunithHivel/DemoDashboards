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
from metrics_editor.storage import create_plan_id


def build_plan(session: Session, request: MetricChangeRequest) -> ChangePlan:
    """
    Build a change plan for the given metric change request.
    
    Uses manual backend logic for simple/bulk operations, AI for complex operations.
    
    Args:
        session: Database session
        request: The change request
        
    Returns:
        ChangePlan with SQL statements
    """
    action = request.action
    
    # Manual actions (simple, deterministic, or bulk operations)
    MANUAL_ACTIONS = {
        "bulk_shift_months",  # Bulk operation - manual is better
    }
    
    if action in MANUAL_ACTIONS:
        print(f"[MANUAL] Building plan with manual logic for action: {action}")
        return _build_plan_manual(session, request)
    else:
        # Use AI for all other actions
        print(f"[AI] Building plan with AI for action: {action}")
        return _build_plan_with_ai(session, request)


def _build_plan_manual(session: Session, request: MetricChangeRequest) -> ChangePlan:
    """Build a plan using manual backend logic (no AI)."""
    action = request.action
    
    if action == "bulk_shift_months":
        from metrics_editor.playbooks.bulk_operations import plan_bulk_shift_months
        return plan_bulk_shift_months(session, request)
    else:
        raise ValueError(f"Manual planning not implemented for action: {action}")


def _build_plan_with_ai(session: Session, request: MetricChangeRequest) -> ChangePlan:
    """Build a plan using AI assistance."""
    from metrics_editor.ai_service import AIMetricService
    from metrics_editor.data_fetcher import DataFetcher
    
    print(f"[AI] Fetching filtered data for {request.metric_id}/{request.action}")
    print(f"[AI] Request options: {request.options}")
    
    # Fetch filtered data
    fetcher = DataFetcher(session)
    filtered_data = fetcher.fetch_filtered_data(request)
    metric_formulas = fetcher.get_metric_formulas(request.metric_id)
    constraints = fetcher.get_constraints(request.metric_id, request.action)
    
    print(f"[AI] Filtered data: {len(filtered_data)} records")
    print(f"[AI] Calling OpenAI API with count={request.options.get('count', 'NOT SET')}...")
    
    # Call AI service
    ai_service = AIMetricService()
    ai_result = ai_service.generate_change_plan(
        metric_id=request.metric_id,
        action=request.action,
        options=request.options,
        filtered_data=filtered_data,
        metric_formulas=metric_formulas,
        constraints=constraints,
    )
    
    selected_ids = ai_result.get('selected_record_ids', [])
    print(f"[AI] AI returned plan with {len(selected_ids)} selected records")
    print(f"[AI] Selected IDs: {selected_ids[:10]}{'...' if len(selected_ids) > 10 else ''}")
    print(f"[AI] AI reasoning: {ai_result.get('reasoning', 'N/A')[:200]}...")
    print(f"[AI] Full AI result keys: {list(ai_result.keys())}")
    
    # Convert AI result to ChangePlan
    plan = _ai_result_to_change_plan(session, request, ai_result)

    # Validate constraints in a transaction before returning
    try:
        from metrics_editor.validators import MetricValidator

        validator = MetricValidator(session)
        affected_metrics = get_affected_metric_ids(request.metric_id)
        is_valid, errors = validator.validate_in_transaction(
            plan.sql_statements,
            plan.sql_params,
            affected_metrics,
            {
                "organization_id": request.scope.organization_id,
                "repo_id": request.scope.repo_id,
                "author_ids": request.scope.author_ids,
                "start_date": request.scope.start_date,
                "end_date": request.scope.end_date,
            },
        )
        if not is_valid:
            raise ValueError("Constraint validation failed:\n" + "\n".join(f"- {e}" for e in errors))
    except Exception as exc:
        raise ValueError(str(exc)) from exc

    return plan


def _ai_result_to_change_plan(
    session: Session,
    request: MetricChangeRequest,
    ai_result: Dict[str, Any],
) -> ChangePlan:
    """Convert AI's JSON result into a ChangePlan using existing playbook logic."""
    from metrics_editor.storage import create_plan_id
    
    action = request.action
    selected_ids = ai_result.get("selected_record_ids", [])
    field_updates = ai_result.get("field_updates", {})
    reasoning = ai_result.get("reasoning", "AI-generated plan")
    org_id = request.scope.organization_id
    
    # Build SQL based on action and AI's selections
    if action == "set_reviewed_count":
        # Mark selected PRs as reviewed
        sql_statements = [
            """
            UPDATE insightly.pull_request
            SET approvedon = createdon + (INTERVAL '1 minute' * :review_minutes),
                approvedby = authorid,
                opentoreviewduration = :review_minutes,
                reviewbranchpr = TRUE
            WHERE id = ANY(:ids) AND organizationid = :org_id;
            """,
            """
            UPDATE insightly.pr_reviewer
            SET approved = TRUE,
                approveddate = (SELECT approvedon FROM insightly.pull_request WHERE id = pullrequestid)
            WHERE pullrequestid = ANY(:ids) AND organizationid = :org_id;
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
        params = [{
            "ids": selected_ids,
            "review_minutes": request.options.get("review_minutes", 180),
            "org_id": org_id,
        }] * len(sql_statements)
    
    elif action == "set_unreviewed_count":
        # Mark selected PRs as unreviewed
        sql_statements = [
            """
            UPDATE insightly.pull_request
            SET approvedon = NULL,
                approvedby = NULL,
                opentoreviewduration = NULL,
                reviewbranchpr = TRUE
            WHERE id = ANY(:ids) AND organizationid = :org_id;
            """,
            """
            UPDATE insightly.pr_reviewer
            SET approved = FALSE,
                approveddate = NULL
            WHERE pullrequestid = ANY(:ids) AND organizationid = :org_id;
            """,
        ]
        params = [{"ids": selected_ids, "org_id": org_id}] * len(sql_statements)
    
    elif action == "set_flashy_reviews":
        # Mark selected PRs as flashy
        flashy_minutes = request.options.get("flashy_minutes", 5)
        sql_statements = [
            """
            UPDATE insightly.pull_request
            SET opentoreviewduration = :flashy_minutes,
                flashyreviewedpr = TRUE,
                reviewbranchpr = TRUE,
                approvedby = COALESCE(approvedby, authorid),
                approvedon = createdon + (INTERVAL '1 minute' * :flashy_minutes)
            WHERE id = ANY(:ids) AND organizationid = :org_id;
            """,
            """
            UPDATE insightly.pr_reviewer
            SET approved = TRUE,
                approveddate = (SELECT approvedon FROM insightly.pull_request WHERE id = pullrequestid)
            WHERE pullrequestid = ANY(:ids) AND organizationid = :org_id;
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
        params = [{"ids": selected_ids, "flashy_minutes": flashy_minutes, "org_id": org_id}] * len(sql_statements)
    
    elif action == "set_large_prs":
        # Update PR size
        target_lines = request.options.get("target_lines", 500)
        added_ratio = request.options.get("added_ratio", 0.6)
        lines_added = round(target_lines * added_ratio)
        lines_removed = target_lines - lines_added
        
        sql_statements = [
            """
            UPDATE insightly.pull_request
            SET linesadded = :lines_added,
                linesremoved = :lines_removed
            WHERE id = ANY(:ids) AND organizationid = :org_id;
            """
        ]
        params = [{
            "ids": selected_ids,
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "org_id": org_id,
        }]
    
    elif action in ["toggle_release_prs", "toggle_hotfix_prs"]:
        column = "releasebranchpr" if action == "toggle_release_prs" else "hotfixpr"
        value = request.options.get("value", True)
        
        sql_statements = [
            f"""
            UPDATE insightly.pull_request
            SET {column} = :value
            WHERE id = ANY(:ids) AND organizationid = :org_id;
            """
        ]
        params = [{"ids": selected_ids, "value": value, "org_id": org_id}]
    
    elif action in ["shift_open_prs", "shift_merged_prs"]:
        # Shift PRs to different month
        target_month = request.options.get("target_month")
        source_month = request.options.get("source_month")
        delta_days = ai_result.get("delta_days")
        if delta_days is None:
            from datetime import date as dt
            target_date = dt.fromisoformat(target_month + "-01")
            source_date = dt.fromisoformat(source_month + "-01")
            delta_days = (target_date - source_date).days

        set_clause = """
            createdon = createdon + (INTERVAL '1 day' * :delta_days),
            approvedon = CASE WHEN approvedon IS NOT NULL THEN approvedon + (INTERVAL '1 day' * :delta_days) ELSE NULL END,
            mergedon = CASE WHEN mergedon IS NOT NULL THEN mergedon + (INTERVAL '1 day' * :delta_days) ELSE NULL END,
            firstcommittedon = CASE WHEN firstcommittedon IS NOT NULL THEN firstcommittedon + (INTERVAL '1 day' * :delta_days) ELSE NULL END,
            reviewedon = CASE WHEN reviewedon IS NOT NULL THEN reviewedon + (INTERVAL '1 day' * :delta_days) ELSE NULL END,
            updatedon = CASE WHEN updatedon IS NOT NULL THEN updatedon + (INTERVAL '1 day' * :delta_days) ELSE NULL END,
            createddate = createddate + (INTERVAL '1 day' * :delta_days),
            modifieddate = modifieddate + (INTERVAL '1 day' * :delta_days)
        """
        sql_statements = [
            f"""
            UPDATE insightly.pull_request
            SET {set_clause}
            WHERE id = ANY(:ids) AND organizationid = :org_id;
            """,
            """
            UPDATE insightly.pr_reviewer
            SET approveddate = CASE WHEN approveddate IS NOT NULL THEN approveddate + (INTERVAL '1 day' * :delta_days) ELSE NULL END,
                createddate = createddate + (INTERVAL '1 day' * :delta_days),
                modifieddate = modifieddate + (INTERVAL '1 day' * :delta_days)
            WHERE pullrequestid = ANY(:ids) AND organizationid = :org_id;
            """,
            """
            UPDATE insightly.pr_update
            SET date = date + (INTERVAL '1 day' * :delta_days),
                createddate = createddate + (INTERVAL '1 day' * :delta_days),
                modifieddate = modifieddate + (INTERVAL '1 day' * :delta_days)
            WHERE pullrequestid = ANY(:ids) AND organizationid = :org_id;
            """,
            """
            UPDATE insightly.pr_comment
            SET createdon = createdon + (INTERVAL '1 day' * :delta_days),
                createddate = createddate + (INTERVAL '1 day' * :delta_days),
                modifieddate = modifieddate + (INTERVAL '1 day' * :delta_days)
            WHERE pullrequestid = ANY(:ids) AND organizationid = :org_id;
            """,
        ]
        params = [{"ids": selected_ids, "delta_days": delta_days, "org_id": org_id}] * len(sql_statements)
    
    elif action in ["scale_review_time", "scale_cycle_time", "scale_deploy_time", "scale_coding_time"]:
        # Scale duration fields
        scale = request.options.get("scale", 1.0)
        column_map = {
            "scale_review_time": "opentoreviewduration",
            "scale_cycle_time": "cycletimeduration",
            "scale_deploy_time": "deploytimeduration",
            "scale_coding_time": "committoopenduration",
        }
        column = column_map[action]
        
        sql_statements = [
            f"""
            UPDATE insightly.pull_request
            SET {column} = ROUND(COALESCE({column}, 0) * :scale)
            WHERE id = ANY(:ids) AND organizationid = :org_id;
            """
        ]
        params = [{"ids": selected_ids, "scale": scale, "org_id": org_id}]
    
    elif action == "set_commit_mix":
        # Update commit work mix
        newwork_pct = request.options.get("newwork_pct", 70)
        rework_pct = request.options.get("rework_pct", 15)
        maintenance_pct = request.options.get("maintenance_pct", 10)
        assistance_pct = request.options.get("assistance_pct", 5)
        
        sql_statements = [
            """
            UPDATE insightly.commit
            SET newwork = ROUND(total_lines * :newwork_pct / 100.0),
                rework = ROUND(total_lines * :rework_pct / 100.0),
                maintenance = ROUND(total_lines * :maintenance_pct / 100.0),
                assistance = GREATEST(total_lines - ROUND(total_lines * :newwork_pct / 100.0)
                                            - ROUND(total_lines * :rework_pct / 100.0)
                                            - ROUND(total_lines * :maintenance_pct / 100.0), 0)
            FROM (
                SELECT id,
                       (COALESCE(newwork, 0) + COALESCE(rework, 0)
                        + COALESCE(maintenance, 0) + COALESCE(assistance, 0)) AS total_lines
                FROM insightly.commit
                WHERE id = ANY(:ids)
            ) AS totals
            WHERE insightly.commit.id = totals.id;
            """
        ]
        params = [{
            "ids": selected_ids,
            "newwork_pct": newwork_pct,
            "rework_pct": rework_pct,
            "maintenance_pct": maintenance_pct,
            "org_id": org_id,
        }]
    
    elif action == "shift_commit_dates":
        # Shift commits to different month
        target_month = request.options.get("target_month")
        source_month = request.options.get("source_month")
        
        from datetime import date as dt
        target_date = dt.fromisoformat(target_month + "-01")
        source_date = dt.fromisoformat(source_month + "-01")
        delta_days = (target_date - source_date).days
        
        sql_statements = [
            """
            UPDATE insightly.commit
            SET date = date + (INTERVAL '1 day' * :delta_days),
                createddate = CASE WHEN createddate IS NOT NULL THEN createddate + (INTERVAL '1 day' * :delta_days) ELSE NULL END,
                modifieddate = CASE WHEN modifieddate IS NOT NULL THEN modifieddate + (INTERVAL '1 day' * :delta_days) ELSE NULL END
            WHERE id = ANY(:ids) AND organizationid = :org_id;
            """,
            """
            UPDATE insightly.commit_files
            SET createddate = createddate + (INTERVAL '1 day' * :delta_days),
                modifieddate = modifieddate + (INTERVAL '1 day' * :delta_days)
            WHERE commitid = ANY(:ids) AND organizationid = :org_id;
            """,
        ]
        params = [{"ids": selected_ids, "delta_days": delta_days, "org_id": org_id}] * len(sql_statements)
    
    else:
        raise ValueError(f"AI planning not implemented for action: {action}")
    
    print(f"[AI] Built SQL plan with {len(sql_statements)} statements")
    
    warnings = [f"AI selected {len(selected_ids)} records"]
    validation_notes = ai_result.get("validation_notes") or []
    if isinstance(validation_notes, list):
        warnings.extend([str(note) for note in validation_notes if note])

    return ChangePlan(
        plan_id=create_plan_id(),
        summary=f"{reasoning} (AI-assisted)",
        sql_statements=[s.strip() for s in sql_statements],
        sql_params=params,
        before_rows=[],
        expected={"updated_records": len(selected_ids)},
        warnings=warnings,
    )


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

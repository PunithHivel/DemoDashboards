from __future__ import annotations

from datetime import date
from typing import Any, Dict, Tuple

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
    clauses = ["organization_id = :org_id"]
    params: Dict[str, Any] = {"org_id": scope.organization_id}
    if scope.repo_id is not None:
        clauses.append("repoid = :repo_id")
        params["repo_id"] = scope.repo_id
    if scope.author_ids:
        clauses.append("authorid = ANY(:author_ids)")
        params["author_ids"] = scope.author_ids
    return " AND ".join(clauses), params


def plan_scale_mttr(session: Session, request: MetricChangeRequest) -> ChangePlan:
    month_value = request.options.get("month")
    scale = float(request.options.get("scale", 1.0))
    if not month_value:
        raise ValueError("month is required (YYYY-MM)")
    if scale <= 0:
        raise ValueError("scale must be > 0")

    start, end = _month_bounds(month_value)
    where_sql, params = _filter_clauses(request.scope)
    params.update({"start": start, "end": end, "scale": scale})

    summary = f"Scale change_requests.duration by {scale} for {month_value}"
    sql = [
        """
        UPDATE insightly.change_requests
        SET duration = ROUND(COALESCE(duration, 0) * :scale),
            start_date = CASE
                WHEN end_date IS NOT NULL THEN end_date - (INTERVAL '1 minute' * ROUND(COALESCE(duration, 0) * :scale))
                ELSE start_date
            END,
            modifieddate = NOW()
        WHERE {where_sql}
          AND start_date >= :start AND start_date < :end;
        """.replace("{where_sql}", where_sql)
    ]

    return ChangePlan(
        plan_id=create_plan_id(),
        summary=summary,
        sql_statements=[s.strip() for s in sql],
        sql_params=[params],
        before_rows=[],
        expected={"updated_change_requests": "all in range"},
    )

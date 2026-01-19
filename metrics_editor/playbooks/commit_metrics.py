from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Tuple

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


def _select_commit_ids(
    session: Session,
    scope,
    start: date,
    end: date,
    limit: int,
) -> List[int]:
    where_sql, params = _filter_clauses(scope)
    params.update({"start": start, "end": end, "limit": limit})
    query = (
        "SELECT id FROM insightly.commit "
        "WHERE "
        f"{where_sql} AND date >= :start AND date < :end "
        "AND type = 'COMMIT' "
        "ORDER BY date, id "
        "LIMIT :limit"
    )
    rows = session.execute(text(query), params).fetchall()
    return [row[0] for row in rows]


def _count_commits(
    session: Session,
    scope,
    start: date,
    end: date,
) -> int:
    where_sql, params = _filter_clauses(scope)
    params.update({"start": start, "end": end})
    query = (
        "SELECT COUNT(*) FROM insightly.commit "
        "WHERE "
        f"{where_sql} AND date >= :start AND date < :end "
        "AND type = 'COMMIT'"
    )
    return int(session.execute(text(query), params).scalar() or 0)


def _normalize_month_list(source_month: str, source_months: List[str] | None, auto_expand: bool) -> List[str]:
    if not auto_expand:
        return [source_month]
    months: List[str] = []
    if source_month:
        months.append(source_month)
    for month in source_months or []:
        if month and month not in months:
            months.append(month)
    return months or [source_month]


def _resolve_commit_groups(
    session: Session,
    scope,
    source_months: List[str],
    target_month: str,
    count: int,
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    target_start, _ = _month_bounds(target_month)
    remaining = count
    groups: list[dict[str, Any]] = []
    warnings: list[str] = []
    before_rows: list[dict[str, Any]] = []

    for month in source_months:
        if remaining <= 0:
            break
        start, end = _month_bounds(month)
        available = _count_commits(session, scope, start, end)
        if available <= 0:
            continue
        take = min(available, remaining)
        ids = _select_commit_ids(session, scope, start, end, take)
        if not ids:
            continue
        delta_days = (target_start - start).days
        groups.append({"source_month": month, "ids": ids, "delta_days": delta_days, "available": available})
        remaining -= len(ids)
        for commit_id in ids:
            before_rows.append(
                {"id": commit_id, "source_month": month, "target_month": target_month, "delta_days": delta_days}
            )

    if remaining > 0:
        raise ValueError(
            f"Only {count - remaining} commits found across {', '.join(source_months)}. "
            f"Reduce the count to {count - remaining} or add more source months."
        )

    if len(source_months) > 1:
        warnings.append(
            "Auto-expand enabled. "
            + ", ".join(
                f"{group['source_month']}: {len(group['ids'])} of {group['available']}" for group in groups
            )
        )

    if len(before_rows) > 200:
        warnings.append("Preview rows truncated to 200 IDs.")
        before_rows = before_rows[:200]

    return groups, warnings, before_rows


def plan_set_commit_mix(session: Session, request: MetricChangeRequest) -> ChangePlan:
    month_value = request.options.get("month")
    if not month_value:
        raise ValueError("month is required (YYYY-MM)")
    newwork_pct = float(request.options.get("newwork_pct", 70))
    rework_pct = float(request.options.get("rework_pct", 15))
    maintenance_pct = float(request.options.get("maintenance_pct", 10))
    assistance_pct = float(request.options.get("assistance_pct", 5))
    total_pct = newwork_pct + rework_pct + maintenance_pct + assistance_pct
    if round(total_pct, 2) != 100.0:
        raise ValueError("Percentages must sum to 100")
    for label, value in {
        "newwork_pct": newwork_pct,
        "rework_pct": rework_pct,
        "maintenance_pct": maintenance_pct,
        "assistance_pct": assistance_pct,
    }.items():
        if value < 0 or value > 100:
            raise ValueError(f"{label} must be between 0 and 100")

    start, end = _month_bounds(month_value)
    where_sql, params = _filter_clauses(request.scope)
    params.update({
        "start": start,
        "end": end,
        "newwork_pct": newwork_pct,
        "rework_pct": rework_pct,
        "maintenance_pct": maintenance_pct,
    })

    summary = f"Set commit work mix in {month_value} to {newwork_pct}/{rework_pct}/{maintenance_pct}/{assistance_pct}"

    sql = [
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
            WHERE {where_sql}
              AND date >= :start AND date < :end
              AND type = 'COMMIT'
        ) AS totals
        WHERE insightly.commit.id = totals.id;
        """.replace("{where_sql}", where_sql)
    ]

    return ChangePlan(
        plan_id=create_plan_id(),
        summary=summary,
        sql_statements=[s.strip() for s in sql],
        sql_params=[params],
        before_rows=[],
        expected={"updated_commits": "all in range"},
    )


def plan_shift_commit_dates(session: Session, request: MetricChangeRequest) -> ChangePlan:
    source_month = request.options.get("source_month")
    target_month = request.options.get("target_month")
    count = int(request.options.get("count", 0))
    auto_expand = bool(request.options.get("auto_expand", False))
    source_months = request.options.get("source_months") or []
    if not source_month or not target_month:
        raise ValueError("source_month and target_month are required")
    if count <= 0:
        raise ValueError("count must be > 0")

    months = _normalize_month_list(source_month, source_months, auto_expand)
    groups, warnings, before_rows = _resolve_commit_groups(
        session,
        request.scope,
        months,
        target_month,
        count,
    )

    summary = f"Shift {count} commits to {target_month}"
    if len(months) == 1:
        summary = f"Shift {count} commits from {months[0]} to {target_month}"
    elif months:
        summary += f" (sources: {', '.join(months)})"

    sql: list[str] = []
    sql_params: list[Dict[str, Any]] = []
    base_sql = [
        """
        UPDATE insightly.commit
        SET date = date + (INTERVAL '1 day' * :delta_days),
            createddate = CASE WHEN createddate IS NOT NULL THEN createddate + (INTERVAL '1 day' * :delta_days) ELSE NULL END,
            modifieddate = CASE WHEN modifieddate IS NOT NULL THEN modifieddate + (INTERVAL '1 day' * :delta_days) ELSE NULL END
        WHERE id = ANY(:ids);
        """,
        """
        UPDATE insightly.commit_files
        SET createddate = createddate + (INTERVAL '1 day' * :delta_days),
            modifieddate = modifieddate + (INTERVAL '1 day' * :delta_days)
        WHERE commitid = ANY(:ids);
        """,
    ]
    for group in groups:
        params = {"ids": group["ids"], "delta_days": group["delta_days"]}
        for statement in base_sql:
            sql.append(statement)
            sql_params.append(params)

    return ChangePlan(
        plan_id=create_plan_id(),
        summary=summary,
        sql_statements=[s.strip() for s in sql],
        sql_params=sql_params,
        before_rows=before_rows,
        expected={"shifted_commits": count},
        warnings=warnings,
    )

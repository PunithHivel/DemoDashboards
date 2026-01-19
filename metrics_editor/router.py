from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.session import get_db_session
from metrics_editor.catalog import load_catalog
from metrics_editor.engine import build_plan, preview_after, preview_impact, snapshot_metric, get_affected_metric_ids
from metrics_editor.eligibility import get_eligible_entities, get_eligible_summary
from metrics_editor.models import (
    ChangeResult,
    EligibilityRequest,
    EligibilityResponse,
    EligibilitySummaryRequest,
    EligibilitySummaryResponse,
    ImpactResponse,
    MetricChangeRequest,
    MetricImpact,
    MetricScope,
)
from repositories.lookup_repository import LookupRepository
from repositories.repo_repository import RepoRepository
from metrics_editor.storage import list_plans, save_plan

router = APIRouter(prefix="/metrics-editor", tags=["metrics-editor"])
_lookup_repository = LookupRepository()
_repo_repository = RepoRepository()


@router.get("/catalog")
def get_catalog() -> Dict[str, Any]:
    return load_catalog()


@router.post("/current")
def get_current_metrics(
    payload: Dict[str, Any],
    session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    metric_id = payload.get("metric_id")
    scope_data = payload.get("scope")
    if not metric_id or not scope_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="metric_id and scope are required")

    try:
        scope = MetricScope(**scope_data)
        if scope.team_id and not scope.author_ids:
            authors = _lookup_repository.list_team_authors(
                session, scope.organization_id, scope.team_id
            )
            scope.author_ids = [author["id"] for author in authors]
        snapshot = snapshot_metric(session, metric_id, scope)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Use dict() for Pydantic v1 or model_dump() for Pydantic v2
    if hasattr(snapshot, 'model_dump'):
        return snapshot.model_dump()
    else:
        return snapshot.dict()


@router.post("/preview")
def preview_change(
    request: MetricChangeRequest,
    session: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        if request.scope.team_id and not request.scope.author_ids:
            authors = _lookup_repository.list_team_authors(
                session, request.scope.organization_id, request.scope.team_id
            )
            request.scope.author_ids = [author["id"] for author in authors]
        plan = build_plan(session, request)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # Use dict() for Pydantic v1 or model_dump() for Pydantic v2
    if hasattr(plan, 'model_dump'):
        return plan.model_dump()
    else:
        return plan.dict()


@router.post("/impact", response_model=ImpactResponse)
def preview_impact_change(
    request: MetricChangeRequest,
    session: Session = Depends(get_db_session),
) -> ImpactResponse:
    try:
        if request.scope.team_id and not request.scope.author_ids:
            authors = _lookup_repository.list_team_authors(
                session, request.scope.organization_id, request.scope.team_id
            )
            request.scope.author_ids = [author["id"] for author in authors]
        plan = build_plan(session, request)
        before = preview_impact(session, request)
        after = preview_after(session, request, plan)
        catalog = load_catalog()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    impacts = []
    for metric_id in get_affected_metric_ids(request.metric_id):
        metric = next((m for m in catalog.get("metrics", []) if m.get("id") == metric_id), None)
        label = metric.get("label") if metric else metric_id
        impacts.append(
            MetricImpact(metric_id=metric_id, label=label, before=before[metric_id], after=after[metric_id])
        )

    return ImpactResponse(metric_id=request.metric_id, affected=impacts, plan=plan)


@router.post("/apply", response_model=ChangeResult)
def apply_change(
    request: MetricChangeRequest,
    session: Session = Depends(get_db_session),
) -> ChangeResult:
    try:
        if request.scope.team_id and not request.scope.author_ids:
            authors = _lookup_repository.list_team_authors(
                session, request.scope.organization_id, request.scope.team_id
            )
            request.scope.author_ids = [author["id"] for author in authors]
        plan = build_plan(session, request)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    rows_affected = 0
    for statement, params in zip(plan.sql_statements, plan.sql_params):
        result = session.execute(text(statement), params)
        if result.rowcount is not None:
            rows_affected += result.rowcount

    # Use dict() for Pydantic v1 or model_dump() for Pydantic v2
    if hasattr(plan, 'model_dump'):
        plan_payload = plan.model_dump()
    else:
        plan_payload = plan.dict()
    
    if hasattr(request, 'model_dump'):
        plan_payload["request"] = request.model_dump()
    else:
        plan_payload["request"] = request.dict()
    
    save_plan(plan_payload)

    return ChangeResult(
        plan_id=plan.plan_id,
        applied=True,
        rows_affected=rows_affected,
        warnings=plan.warnings,
    )


@router.get("/history")
def get_history() -> Dict[str, Any]:
    return {"plans": list_plans()}


@router.post("/eligible", response_model=EligibilityResponse)
def get_eligible(
    request: EligibilityRequest,
    session: Session = Depends(get_db_session),
) -> EligibilityResponse:
    try:
        eligible = get_eligible_entities(session, request)
        teams = _lookup_repository.list_teams(session, request.organization_id)
        team_lookup = {team["id"]: team for team in teams}
        authors = _lookup_repository.list_authors(session, request.organization_id)
        author_lookup = {author["id"]: author for author in authors}
        repos = _repo_repository.list_repos(session, request.organization_id)
        repo_lookup = {repo["id"]: repo for repo in repos}

        for team in eligible.teams:
            info = team_lookup.get(team.id)
            if info:
                team.label = f"{info['id']} - {info.get('name') or ''}".strip()

        for author in eligible.authors:
            info = author_lookup.get(author.id)
            if info:
                name = info.get("name") or "Unknown"
                username = info.get("username") or "unknown"
                author.label = f"{info['id']} - {name} ({username})"

        for repo in eligible.repos:
            info = repo_lookup.get(repo.id)
            if info:
                repo.label = f"{info['id']} - {info.get('name') or info.get('slug') or ''}".strip()
        return eligible
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/eligible-summary", response_model=EligibilitySummaryResponse)
def get_eligible_summary_endpoint(
    request: EligibilitySummaryRequest,
    session: Session = Depends(get_db_session),
) -> EligibilitySummaryResponse:
    try:
        if request.scope.team_id and not request.scope.author_ids:
            authors = _lookup_repository.list_team_authors(
                session, request.scope.organization_id, request.scope.team_id
            )
            request.scope.author_ids = [author["id"] for author in authors]
        return get_eligible_summary(session, request)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

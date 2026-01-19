from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MetricScope(BaseModel):
    organization_id: int = Field(..., description="Organization ID")
    repo_id: Optional[int] = Field(None, description="Repo ID to scope changes")
    team_id: Optional[int] = Field(None, description="Team ID to scope changes")
    author_ids: Optional[List[int]] = Field(None, description="Limit to author IDs")
    start_date: date = Field(..., description="Inclusive start date")
    end_date: date = Field(..., description="Exclusive end date")


class MetricTarget(BaseModel):
    mode: str = Field(..., description="absolute or delta")
    value: float = Field(..., description="Target value or delta")
    unit: str = Field(..., description="count, minutes, percent")


class MetricChangeRequest(BaseModel):
    metric_id: str
    action: str
    scope: MetricScope
    target: Optional[MetricTarget] = None
    options: Dict[str, Any] = Field(default_factory=dict)


class MetricPoint(BaseModel):
    period: str
    value: float


class MetricSnapshot(BaseModel):
    metric_id: str
    scope: MetricScope
    total_value: float
    by_period: List[MetricPoint]


class ChangePlan(BaseModel):
    plan_id: str
    summary: str
    sql_statements: List[str]
    sql_params: List[Dict[str, Any]]
    before_rows: List[Dict[str, Any]]
    expected: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)


class ChangeResult(BaseModel):
    plan_id: str
    applied: bool
    rows_affected: int
    warnings: List[str] = Field(default_factory=list)


class EligibilityRequest(BaseModel):
    metric_id: str
    action: Optional[str] = None
    organization_id: int
    repo_id: Optional[int] = None
    team_id: Optional[int] = None
    author_ids: Optional[List[int]] = None
    start_date: date
    end_date: date


class EligibleEntity(BaseModel):
    id: int
    count: int
    label: Optional[str] = None


class EligibilityResponse(BaseModel):
    metric_id: str
    repos: List[EligibleEntity] = Field(default_factory=list)
    teams: List[EligibleEntity] = Field(default_factory=list)
    authors: List[EligibleEntity] = Field(default_factory=list)


class EligibilitySummaryRequest(BaseModel):
    metric_id: str
    action: str
    scope: MetricScope
    options: Dict[str, Any] = Field(default_factory=dict)


class EligibilitySummaryPoint(BaseModel):
    period: str
    eligible_count: int


class EligibilitySummaryResponse(BaseModel):
    metric_id: str
    action: str
    by_period: List[EligibilitySummaryPoint] = Field(default_factory=list)


class MetricImpact(BaseModel):
    metric_id: str
    label: str
    before: MetricSnapshot
    after: MetricSnapshot


class ImpactResponse(BaseModel):
    metric_id: str
    affected: List[MetricImpact]
    plan: ChangePlan

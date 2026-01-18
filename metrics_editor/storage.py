from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

LOG_DIR = Path(__file__).resolve().parent.parent / "logs" / "metric_editor"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def create_plan_id() -> str:
    return uuid4().hex


def save_plan(plan: Dict[str, Any]) -> str:
    plan_id = plan.get("plan_id") or create_plan_id()
    plan["plan_id"] = plan_id
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = LOG_DIR / f"{timestamp}_{plan_id}.json"
    path.write_text(json.dumps(plan, indent=2, default=str))
    return plan_id


def list_plans(limit: int = 50) -> List[Dict[str, Any]]:
    entries = sorted(LOG_DIR.glob("*.json"), reverse=True)
    plans: List[Dict[str, Any]] = []
    for path in entries[:limit]:
        plans.append(json.loads(path.read_text()))
    return plans


def load_plan(plan_id: str) -> Dict[str, Any]:
    for path in LOG_DIR.glob(f"*_{plan_id}.json"):
        return json.loads(path.read_text())
    raise FileNotFoundError(f"Plan not found: {plan_id}")

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

CATALOG_PATH = Path(__file__).resolve().parent.parent / "config" / "metric_catalog.json"


def load_catalog() -> Dict[str, Any]:
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(f"Metric catalog not found: {CATALOG_PATH}")
    return json.loads(CATALOG_PATH.read_text())


def get_metric(catalog: Dict[str, Any], metric_id: str) -> Optional[Dict[str, Any]]:
    for metric in catalog.get("metrics", []):
        if metric.get("id") == metric_id:
            return metric
    return None

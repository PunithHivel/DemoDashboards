"""
Data Fetcher for AI Service.

Fetches and filters data from database based on user's request,
then prepares it for the AI service.
"""

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from metrics_editor.models import MetricChangeRequest


class DataFetcher:
    """Fetches filtered data for AI analysis."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def fetch_filtered_data(self, request: MetricChangeRequest) -> List[Dict[str, Any]]:
        """
        Fetch filtered data based on the request.
        
        Returns list of records that match the user's filters and action.
        """
        metric_id = request.metric_id
        action = request.action
        scope = request.scope
        options = request.options
        
        # Determine which table and filters based on metric/action
        if metric_id in self._get_pr_metrics():
            return self._fetch_pr_data(action, scope, options)
        elif metric_id in self._get_commit_metrics():
            return self._fetch_commit_data(action, scope, options)
        else:
            return []
    
    def _get_pr_metrics(self) -> set:
        """Get set of PR-related metrics."""
        return {
            "pr_opened", "pr_merged", "pr_reviewed", "pr_unreviewed",
            "flashy_reviews", "large_prs", "review_time", "cycle_time",
            "delivery_lead_time", "deploy_time", "coding_time",
            "release_prs", "deployment_frequency", "hotfix_prs", "mttr",
        }
    
    def _get_commit_metrics(self) -> set:
        """Get set of commit-related metrics."""
        return {"rework_pct", "newwork_pct", "maintenance_pct", "commit_frequency"}
    
    def _fetch_pr_data(
        self,
        action: str,
        scope,
        options: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Fetch PR data based on action and scope."""
        
        # Build base query
        columns = [
            "id", "state", "createdon", "mergedon", "approvedon",
            "linesadded", "linesremoved", "opentoreviewduration",
            "cycletimeduration", "deploytimeduration", "committoopenduration",
            "releasebranchpr", "hotfixpr", "reviewbranchpr", "flashyreviewedpr",
            "authorid", "repoid", "approvedby",
        ]
        
        # Build WHERE clause
        where_clauses = ["organizationid = :org_id"]
        params: Dict[str, Any] = {"org_id": scope.organization_id}
        
        if scope.repo_id:
            where_clauses.append("repoid = :repo_id")
            params["repo_id"] = scope.repo_id
        
        if scope.author_ids:
            where_clauses.append("authorid = ANY(:author_ids)")
            params["author_ids"] = scope.author_ids
        
        # Add action-specific filters
        action_filters = self._get_action_filters(action, options)
        where_clauses.extend(action_filters["where"])
        params.update(action_filters["params"])
        
        # Add date filters
        date_field = action_filters.get("date_field", "mergedon")
        where_clauses.append(f"{date_field} >= :start_date")
        where_clauses.append(f"{date_field} < :end_date")
        params["start_date"] = scope.start_date
        params["end_date"] = scope.end_date
        
        # Build and execute query
        query = f"""
            SELECT {', '.join(columns)}
            FROM insightly.pull_request
            WHERE {' AND '.join(where_clauses)}
            ORDER BY {date_field}, id
            LIMIT 1000
        """
        
        result = self.session.execute(text(query), params)
        rows = [dict(row._mapping) for row in result]
        
        return rows
    
    def _fetch_commit_data(
        self,
        action: str,
        scope,
        options: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Fetch commit data based on action and scope."""
        
        columns = [
            "id", "date", "type", "newwork", "rework",
            "maintenance", "assistance", "authorid", "repoid",
        ]
        
        where_clauses = ["organizationid = :org_id", "type = 'COMMIT'"]
        params: Dict[str, Any] = {"org_id": scope.organization_id}
        
        if scope.repo_id:
            where_clauses.append("repoid = :repo_id")
            params["repo_id"] = scope.repo_id
        
        if scope.author_ids:
            where_clauses.append("authorid = ANY(:author_ids)")
            params["author_ids"] = scope.author_ids
        
        where_clauses.append("date >= :start_date")
        where_clauses.append("date < :end_date")
        params["start_date"] = scope.start_date
        params["end_date"] = scope.end_date
        
        query = f"""
            SELECT {', '.join(columns)}
            FROM insightly.commit
            WHERE {' AND '.join(where_clauses)}
            ORDER BY date, id
            LIMIT 1000
        """
        
        result = self.session.execute(text(query), params)
        rows = [dict(row._mapping) for row in result]
        
        return rows
    
    def _get_action_filters(self, action: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Get action-specific filters."""
        
        if action in ["set_reviewed_count", "set_unreviewed_count"]:
            return {
                "where": ["state = 'MERGED'"],
                "params": {},
                "date_field": "mergedon",
            }
        
        elif action == "shift_open_prs":
            return {
                "where": ["state = 'OPEN'"],
                "params": {},
                "date_field": "createdon",
            }
        
        elif action == "shift_merged_prs":
            return {
                "where": ["state = 'MERGED'"],
                "params": {},
                "date_field": "mergedon",
            }
        
        elif action == "set_flashy_reviews":
            return {
                "where": [
                    "state = 'MERGED'",
                    "approvedon IS NOT NULL",
                    "reviewbranchpr = TRUE",
                ],
                "params": {},
                "date_field": "mergedon",
            }
        
        elif action == "set_large_prs":
            return {
                "where": ["state = 'MERGED'"],
                "params": {},
                "date_field": "mergedon",
            }
        
        elif action in ["toggle_release_prs", "toggle_hotfix_prs"]:
            return {
                "where": ["state = 'MERGED'"],
                "params": {},
                "date_field": "mergedon",
            }
        
        elif action in ["scale_review_time", "scale_cycle_time", "scale_deploy_time", "scale_coding_time"]:
            return {
                "where": ["state = 'MERGED'"],
                "params": {},
                "date_field": "mergedon",
            }
        
        else:
            return {
                "where": ["state = 'MERGED'"],
                "params": {},
                "date_field": "mergedon",
            }
    
    def get_metric_formulas(self, metric_id: str) -> Dict[str, str]:
        """Get formulas for the metric and related metrics."""
        formulas = {
            "pr_reviewed": "COUNT(PRs WHERE state='MERGED' AND approvedon IS NOT NULL AND reviewbranchpr=TRUE)",
            "pr_unreviewed": "COUNT(PRs WHERE state='MERGED' AND approvedon IS NULL AND reviewbranchpr=TRUE)",
            "flashy_reviews": "COUNT(PRs WHERE opentoreviewduration < 5 AND (linesadded + linesremoved) > 400)",
            "large_prs": "COUNT(PRs WHERE (linesadded + linesremoved) > 400)",
            "cycle_time": "AVG(committoopenduration + opentoreviewduration + deploytimeduration)",
            "review_time": "AVG(opentoreviewduration)",
            "deploy_time": "AVG(deploytimeduration)",
            "coding_time": "AVG(committoopenduration)",
            "release_prs": "COUNT(PRs WHERE releasebranchpr = TRUE)",
            "hotfix_prs": "COUNT(PRs WHERE hotfixpr = TRUE)",
            "newwork_pct": "SUM(newwork) * 100 / SUM(newwork + rework + maintenance + assistance)",
            "rework_pct": "SUM(rework + assistance) * 100 / SUM(newwork + rework + maintenance + assistance)",
            "maintenance_pct": "SUM(maintenance) * 100 / SUM(newwork + rework + maintenance + assistance)",
        }
        
        return {metric_id: formulas.get(metric_id, "Unknown")}
    
    def get_constraints(self, metric_id: str, action: str) -> List[str]:
        """Get constraints that must be preserved."""
        constraints = []
        
        if action in ["set_reviewed_count", "set_unreviewed_count"]:
            constraints.extend([
                "Reviewed + Unreviewed = Total Merged (for review branch PRs)",
                "Flashy reviews ≤ Reviewed PRs",
            ])
        
        if action == "set_flashy_reviews":
            constraints.extend([
                "Flashy reviews ≤ Reviewed PRs",
                "Flashy reviews require: review time < 5 min AND size > 400 lines",
            ])
        
        if action in ["toggle_release_prs", "toggle_hotfix_prs"]:
            constraints.append("Hotfix PRs ≤ Release PRs")
        
        if action in ["scale_review_time", "scale_cycle_time", "scale_deploy_time", "scale_coding_time"]:
            constraints.append("Cycle time = Coding time + Review time + Deploy time")
        
        if action == "set_commit_mix":
            constraints.append("Work mix percentages must sum to 100%")
        
        return constraints

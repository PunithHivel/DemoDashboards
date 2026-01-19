"""
MCP Tool Registry for AI-driven metric changes.

This module provides tools that the AI can use to inspect database state,
validate changes, and understand metric relationships.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from metrics_editor.catalog import load_catalog, get_metric
from metrics_editor.models import MetricScope


class MCPToolRegistry:
    """
    Registry of MCP tools available to the AI.
    
    These tools allow the AI to:
    1. Inspect current database state
    2. Validate proposed changes
    3. Understand metric formulas and dependencies
    4. Check constraints
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.catalog = load_catalog()
    
    def inspect_pr_data(
        self,
        filters: Dict[str, Any],
        columns: Optional[List[str]] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Inspect pull request data.
        
        Args:
            filters: Filters to apply (e.g., {"state": "MERGED", "date_range": {...}})
            columns: Columns to retrieve (default: common columns)
            limit: Max rows to return
            
        Returns:
            Dict with rows, summary statistics, and metadata
        """
        if columns is None:
            columns = [
                "id",
                "state",
                "createdon",
                "mergedon",
                "approvedon",
                "linesadded",
                "linesremoved",
                "opentoreviewduration",
                "cycletimeduration",
                "deploytimeduration",
                "committoopenduration",
                "releasebranchpr",
                "hotfixpr",
                "reviewbranchpr",
                "authorid",
                "repoid",
            ]
        
        # Build WHERE clause from filters
        where_clauses = []
        params: Dict[str, Any] = {}
        
        if "state" in filters:
            where_clauses.append("state = :state")
            params["state"] = filters["state"]
        
        if "date_range" in filters:
            date_range = filters["date_range"]
            date_field = date_range.get("field", "mergedon")
            if "start" in date_range:
                where_clauses.append(f"{date_field} >= :start_date")
                params["start_date"] = date_range["start"]
            if "end" in date_range:
                where_clauses.append(f"{date_field} < :end_date")
                params["end_date"] = date_range["end"]
        
        if "organization_id" in filters:
            where_clauses.append("organizationid = :org_id")
            params["org_id"] = filters["organization_id"]
        
        if "repo_id" in filters:
            where_clauses.append("repoid = :repo_id")
            params["repo_id"] = filters["repo_id"]
        
        if "author_ids" in filters:
            where_clauses.append("authorid = ANY(:author_ids)")
            params["author_ids"] = filters["author_ids"]
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Build query
        column_list = ", ".join(columns)
        query = f"""
            SELECT {column_list}
            FROM insightly.pull_request
            WHERE {where_sql}
            ORDER BY id
            LIMIT :limit
        """
        params["limit"] = limit
        
        # Execute query
        result = self.session.execute(text(query), params)
        rows = [dict(row._mapping) for row in result]
        
        # Get summary statistics
        summary_query = f"""
            SELECT
                COUNT(*) as total_count,
                COUNT(CASE WHEN state = 'MERGED' THEN 1 END) as merged_count,
                COUNT(CASE WHEN state = 'OPEN' THEN 1 END) as open_count,
                COUNT(CASE WHEN approvedon IS NOT NULL THEN 1 END) as reviewed_count,
                COUNT(CASE WHEN approvedon IS NULL AND state = 'MERGED' THEN 1 END) as unreviewed_count,
                AVG(CASE WHEN opentoreviewduration IS NOT NULL THEN opentoreviewduration END) as avg_review_time,
                AVG(CASE WHEN cycletimeduration IS NOT NULL THEN cycletimeduration END) as avg_cycle_time
            FROM insightly.pull_request
            WHERE {where_sql}
        """
        summary_result = self.session.execute(text(summary_query), params)
        summary = dict(summary_result.mappings().first())
        
        return {
            "rows": rows,
            "count": len(rows),
            "summary": summary,
            "filters_applied": filters,
            "columns": columns,
        }
    
    def inspect_commit_data(
        self,
        filters: Dict[str, Any],
        columns: Optional[List[str]] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Inspect commit data.
        
        Args:
            filters: Filters to apply
            columns: Columns to retrieve
            limit: Max rows to return
            
        Returns:
            Dict with rows, summary statistics, and metadata
        """
        if columns is None:
            columns = [
                "id",
                "date",
                "type",
                "newwork",
                "rework",
                "maintenance",
                "assistance",
                "authorid",
                "repoid",
            ]
        
        # Build WHERE clause
        where_clauses = []
        params: Dict[str, Any] = {}
        
        if "type" in filters:
            where_clauses.append("type = :type")
            params["type"] = filters["type"]
        else:
            where_clauses.append("type = 'COMMIT'")
        
        if "date_range" in filters:
            date_range = filters["date_range"]
            if "start" in date_range:
                where_clauses.append("date >= :start_date")
                params["start_date"] = date_range["start"]
            if "end" in date_range:
                where_clauses.append("date < :end_date")
                params["end_date"] = date_range["end"]
        
        if "organization_id" in filters:
            where_clauses.append("organizationid = :org_id")
            params["org_id"] = filters["organization_id"]
        
        if "repo_id" in filters:
            where_clauses.append("repoid = :repo_id")
            params["repo_id"] = filters["repo_id"]
        
        if "author_ids" in filters:
            where_clauses.append("authorid = ANY(:author_ids)")
            params["author_ids"] = filters["author_ids"]
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Build query
        column_list = ", ".join(columns)
        query = f"""
            SELECT {column_list}
            FROM insightly.commit
            WHERE {where_sql}
            ORDER BY date, id
            LIMIT :limit
        """
        params["limit"] = limit
        
        # Execute query
        result = self.session.execute(text(query), params)
        rows = [dict(row._mapping) for row in result]
        
        # Get summary statistics
        summary_query = f"""
            SELECT
                COUNT(*) as total_count,
                SUM(newwork) as total_newwork,
                SUM(rework) as total_rework,
                SUM(maintenance) as total_maintenance,
                SUM(assistance) as total_assistance,
                SUM(newwork + rework + maintenance + assistance) as total_lines
            FROM insightly.commit
            WHERE {where_sql}
        """
        summary_result = self.session.execute(text(summary_query), params)
        summary = dict(summary_result.mappings().first())
        
        # Calculate percentages
        total_lines = summary.get("total_lines") or 0
        if total_lines > 0:
            summary["newwork_pct"] = (summary.get("total_newwork") or 0) * 100.0 / total_lines
            summary["rework_pct"] = (summary.get("total_rework") or 0) * 100.0 / total_lines
            summary["maintenance_pct"] = (summary.get("total_maintenance") or 0) * 100.0 / total_lines
            summary["assistance_pct"] = (summary.get("total_assistance") or 0) * 100.0 / total_lines
        
        return {
            "rows": rows,
            "count": len(rows),
            "summary": summary,
            "filters_applied": filters,
            "columns": columns,
        }
    
    def validate_metric_impact(
        self,
        metric_id: str,
        proposed_change: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate how a proposed change would impact a metric and its dependencies.
        
        Args:
            metric_id: The metric being changed
            proposed_change: Description of the change
            
        Returns:
            Dict with validation results and warnings
        """
        metric = get_metric(self.catalog, metric_id)
        if not metric:
            return {
                "valid": False,
                "error": f"Unknown metric: {metric_id}",
            }
        
        # Get affected metrics
        affects = metric.get("affects", [])
        
        # Build validation result
        validation = {
            "valid": True,
            "metric_id": metric_id,
            "metric_label": metric.get("label"),
            "affects": affects,
            "warnings": [],
            "constraints": [],
        }
        
        # Check specific constraints based on metric type
        if metric_id in ["pr_reviewed", "pr_unreviewed"]:
            validation["constraints"].append(
                "Reviewed + Unreviewed must equal total merged review branch PRs"
            )
            validation["warnings"].append(
                "Changing review status affects flashy_reviews if review time < 5 min"
            )
        
        if metric_id == "flashy_reviews":
            validation["constraints"].append("Flashy reviews <= Reviewed PRs")
            validation["constraints"].append("Flashy reviews require: review time < 5 min AND size > 400 lines")
        
        if metric_id == "hotfix_prs":
            validation["constraints"].append("Hotfix PRs <= Release PRs")
        
        if metric_id == "release_prs":
            validation["constraints"].append("Release PRs >= Hotfix PRs")
        
        if metric_id in ["review_time", "cycle_time", "deploy_time", "coding_time"]:
            validation["constraints"].append(
                "Cycle time = Coding time + Review time + Deploy time"
            )
            validation["warnings"].append(
                "Scaling one duration component requires recalculating cycle time"
            )
        
        if metric_id in ["newwork_pct", "rework_pct", "maintenance_pct"]:
            validation["constraints"].append(
                "Work mix percentages must sum to 100%"
            )
            validation["warnings"].append(
                "Changing one percentage affects the others"
            )
        
        return validation
    
    def get_metric_formula(self, metric_id: str) -> Dict[str, Any]:
        """
        Get the formula and dependencies for a metric.
        
        Args:
            metric_id: The metric ID
            
        Returns:
            Dict with formula, source, dependencies, and calculation logic
        """
        metric = get_metric(self.catalog, metric_id)
        if not metric:
            return {
                "error": f"Unknown metric: {metric_id}",
            }
        
        result = {
            "metric_id": metric_id,
            "label": metric.get("label"),
            "unit": metric.get("unit"),
            "source": metric.get("source"),
            "affects": metric.get("affects", []),
            "actions": metric.get("actions", []),
        }
        
        # Add specific formula information
        if metric_id == "pr_reviewed":
            result["formula"] = "COUNT(PRs WHERE state='MERGED' AND approvedon IS NOT NULL AND reviewbranchpr=TRUE)"
            result["fields"] = ["state", "approvedon", "reviewbranchpr"]
        
        elif metric_id == "pr_unreviewed":
            result["formula"] = "COUNT(PRs WHERE state='MERGED' AND approvedon IS NULL AND reviewbranchpr=TRUE)"
            result["fields"] = ["state", "approvedon", "reviewbranchpr"]
        
        elif metric_id == "flashy_reviews":
            result["formula"] = "COUNT(PRs WHERE opentoreviewduration < 5 AND (linesadded + linesremoved) > 400)"
            result["fields"] = ["opentoreviewduration", "linesadded", "linesremoved"]
        
        elif metric_id == "cycle_time":
            result["formula"] = "AVG(committoopenduration + opentoreviewduration + deploytimeduration)"
            result["fields"] = ["committoopenduration", "opentoreviewduration", "deploytimeduration", "cycletimeduration"]
        
        elif metric_id == "deployment_frequency":
            result["formula"] = "SUM(releasebranchpr=TRUE) / COUNT(state='MERGED')"
            result["fields"] = ["releasebranchpr", "state"]
        
        elif metric_id == "newwork_pct":
            result["formula"] = "SUM(newwork) * 100 / SUM(newwork + rework + maintenance + assistance)"
            result["fields"] = ["newwork", "rework", "maintenance", "assistance"]
        
        elif metric_id == "rework_pct":
            result["formula"] = "SUM(rework + assistance) * 100 / SUM(newwork + rework + maintenance + assistance)"
            result["fields"] = ["newwork", "rework", "maintenance", "assistance"]
        
        return result
    
    def get_pr_summary(self, scope: MetricScope) -> Dict[str, Any]:
        """Get a summary of PR counts for a scope."""
        params = {
            "org_id": scope.organization_id,
            "start": scope.start_date,
            "end": scope.end_date,
        }
        
        where_clauses = ["organizationid = :org_id"]
        if scope.repo_id:
            where_clauses.append("repoid = :repo_id")
            params["repo_id"] = scope.repo_id
        if scope.author_ids:
            where_clauses.append("authorid = ANY(:author_ids)")
            params["author_ids"] = scope.author_ids
        
        where_sql = " AND ".join(where_clauses)
        
        query = f"""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN state = 'MERGED' THEN 1 END) as merged,
                COUNT(CASE WHEN state = 'OPEN' THEN 1 END) as open,
                COUNT(CASE WHEN approvedon IS NOT NULL THEN 1 END) as reviewed,
                COUNT(CASE WHEN approvedon IS NULL AND state = 'MERGED' THEN 1 END) as unreviewed
            FROM insightly.pull_request
            WHERE {where_sql}
              AND createdon >= :start AND createdon < :end
        """
        
        result = self.session.execute(text(query), params)
        return dict(result.mappings().first())
    
    def get_commit_summary(self, scope: MetricScope) -> Dict[str, Any]:
        """Get a summary of commit counts for a scope."""
        params = {
            "org_id": scope.organization_id,
            "start": scope.start_date,
            "end": scope.end_date,
        }
        
        where_clauses = ["organizationid = :org_id", "type = 'COMMIT'"]
        if scope.repo_id:
            where_clauses.append("repoid = :repo_id")
            params["repo_id"] = scope.repo_id
        if scope.author_ids:
            where_clauses.append("authorid = ANY(:author_ids)")
            params["author_ids"] = scope.author_ids
        
        where_sql = " AND ".join(where_clauses)
        
        query = f"""
            SELECT
                COUNT(*) as total,
                SUM(newwork + rework + maintenance + assistance) as total_lines
            FROM insightly.commit
            WHERE {where_sql}
              AND date >= :start AND date < :end
        """
        
        result = self.session.execute(text(query), params)
        return dict(result.mappings().first())

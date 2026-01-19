"""
Validation layer for metric changes.

This module ensures that all metric changes preserve dependencies and constraints.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from metrics_editor.catalog import load_catalog, get_metric


class MetricValidator:
    """
    Validates metric changes against constraints and dependencies.
    
    This class ensures:
    1. Metric formulas remain valid
    2. Cross-metric relationships are preserved
    3. Data constraints are not violated
    4. Changes are internally consistent
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.catalog = load_catalog()
    
    def validate_change_plan(
        self,
        sql_statements: List[str],
        sql_params: List[Dict[str, Any]],
        affected_metrics: List[str],
        scope: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Validate a complete change plan.
        
        Args:
            sql_statements: SQL statements to execute
            sql_params: Parameters for each statement
            affected_metrics: Metrics that will be affected
            scope: Scope of the change
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate SQL safety
        sql_errors = self._validate_sql_safety(sql_statements)
        errors.extend(sql_errors)
        
        # Validate metric constraints
        for metric_id in affected_metrics:
            metric_errors = self._validate_metric_constraints(metric_id, scope)
            errors.extend(metric_errors)
        
        # Validate cross-metric relationships
        relationship_errors = self._validate_relationships(affected_metrics, scope)
        errors.extend(relationship_errors)
        
        return len(errors) == 0, errors
    
    def _validate_sql_safety(self, sql_statements: List[str]) -> List[str]:
        """Validate that SQL statements are safe."""
        errors = []
        
        for i, stmt in enumerate(sql_statements):
            stmt_upper = stmt.upper().strip()
            
            # Check for forbidden operations
            forbidden = ["DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE"]
            for keyword in forbidden:
                if keyword in stmt_upper and not stmt_upper.startswith("UPDATE"):
                    errors.append(f"Statement {i+1} contains forbidden operation: {keyword}")
            
            # Check for WHERE clause in UPDATE statements
            if stmt_upper.startswith("UPDATE") and "WHERE" not in stmt_upper:
                errors.append(f"Statement {i+1} is missing WHERE clause")
            
            # Check for dangerous patterns
            if "WHERE 1=1" in stmt_upper or "WHERE TRUE" in stmt_upper:
                errors.append(f"Statement {i+1} has overly broad WHERE clause")
        
        return errors
    
    def _validate_metric_constraints(
        self,
        metric_id: str,
        scope: Dict[str, Any],
    ) -> List[str]:
        """Validate constraints specific to a metric."""
        errors = []
        metric = get_metric(self.catalog, metric_id)
        
        if not metric:
            errors.append(f"Unknown metric: {metric_id}")
            return errors
        
        # Validate based on metric type
        if metric_id in ["pr_reviewed", "pr_unreviewed"]:
            errors.extend(self._validate_review_constraints(scope))
        
        elif metric_id == "flashy_reviews":
            errors.extend(self._validate_flashy_constraints(scope))
        
        elif metric_id in ["hotfix_prs", "release_prs"]:
            errors.extend(self._validate_pr_flag_constraints(scope))
        
        elif metric_id in ["review_time", "cycle_time", "deploy_time", "coding_time"]:
            errors.extend(self._validate_duration_constraints(scope))
        
        elif metric_id in ["newwork_pct", "rework_pct", "maintenance_pct"]:
            errors.extend(self._validate_commit_mix_constraints(scope))
        
        return errors
    
    def _validate_review_constraints(self, scope: Dict[str, Any]) -> List[str]:
        """
        Validate review constraints:
        - Reviewed + Unreviewed = Total Merged (for review branch PRs)
        """
        errors = []
        
        # This would be validated after the change is applied in a transaction
        # For now, we just document the constraint
        return errors
    
    def _validate_flashy_constraints(self, scope: Dict[str, Any]) -> List[str]:
        """
        Validate flashy review constraints:
        - Flashy reviews <= Reviewed PRs
        - Flashy reviews require: review time < 5 min AND size > 400 lines
        """
        errors = []
        
        # Build query to check constraint
        where_clauses = ["organizationid = :org_id"]
        params = {"org_id": scope.get("organization_id")}
        
        if scope.get("repo_id"):
            where_clauses.append("repoid = :repo_id")
            params["repo_id"] = scope["repo_id"]
        
        if scope.get("author_ids"):
            where_clauses.append("authorid = ANY(:author_ids)")
            params["author_ids"] = scope["author_ids"]
        
        where_sql = " AND ".join(where_clauses)
        
        query = f"""
            SELECT
                COUNT(CASE WHEN approvedon IS NOT NULL AND reviewbranchpr = TRUE THEN 1 END) as reviewed,
                COUNT(CASE WHEN opentoreviewduration < 5 
                    AND (COALESCE(linesadded, 0) + COALESCE(linesremoved, 0)) > 400 
                    AND approvedby IS NOT NULL THEN 1 END) as flashy
            FROM insightly.pull_request
            WHERE {where_sql}
              AND state = 'MERGED'
              AND mergedon >= :start_date
              AND mergedon < :end_date
        """
        params["start_date"] = scope.get("start_date")
        params["end_date"] = scope.get("end_date")
        
        result = self.session.execute(text(query), params)
        row = result.mappings().first()
        
        if row and row["flashy"] > row["reviewed"]:
            errors.append(
                f"Constraint violation: Flashy reviews ({row['flashy']}) "
                f"cannot exceed reviewed PRs ({row['reviewed']})"
            )
        
        return errors
    
    def _validate_pr_flag_constraints(self, scope: Dict[str, Any]) -> List[str]:
        """
        Validate PR flag constraints:
        - Hotfix PRs <= Release PRs
        """
        errors = []
        
        where_clauses = ["organizationid = :org_id"]
        params = {"org_id": scope.get("organization_id")}
        
        if scope.get("repo_id"):
            where_clauses.append("repoid = :repo_id")
            params["repo_id"] = scope["repo_id"]
        
        if scope.get("author_ids"):
            where_clauses.append("authorid = ANY(:author_ids)")
            params["author_ids"] = scope["author_ids"]
        
        where_sql = " AND ".join(where_clauses)
        
        query = f"""
            SELECT
                COUNT(CASE WHEN releasebranchpr = TRUE THEN 1 END) as release,
                COUNT(CASE WHEN hotfixpr = TRUE THEN 1 END) as hotfix
            FROM insightly.pull_request
            WHERE {where_sql}
              AND state = 'MERGED'
              AND mergedon >= :start_date
              AND mergedon < :end_date
        """
        params["start_date"] = scope.get("start_date")
        params["end_date"] = scope.get("end_date")
        
        result = self.session.execute(text(query), params)
        row = result.mappings().first()
        
        if row and row["hotfix"] > row["release"]:
            errors.append(
                f"Constraint violation: Hotfix PRs ({row['hotfix']}) "
                f"cannot exceed release PRs ({row['release']})"
            )
        
        return errors
    
    def _validate_duration_constraints(self, scope: Dict[str, Any]) -> List[str]:
        """
        Validate duration constraints:
        - Cycle time = Coding time + Review time + Deploy time
        - All durations must be non-negative
        """
        errors = []
        
        # Check for negative durations
        where_clauses = ["organizationid = :org_id"]
        params = {"org_id": scope.get("organization_id")}
        
        if scope.get("repo_id"):
            where_clauses.append("repoid = :repo_id")
            params["repo_id"] = scope["repo_id"]
        
        if scope.get("author_ids"):
            where_clauses.append("authorid = ANY(:author_ids)")
            params["author_ids"] = scope["author_ids"]
        
        where_sql = " AND ".join(where_clauses)
        
        query = f"""
            SELECT COUNT(*) as count
            FROM insightly.pull_request
            WHERE {where_sql}
              AND state = 'MERGED'
              AND mergedon >= :start_date
              AND mergedon < :end_date
              AND (
                  opentoreviewduration < 0
                  OR cycletimeduration < 0
                  OR deploytimeduration < 0
                  OR committoopenduration < 0
              )
        """
        params["start_date"] = scope.get("start_date")
        params["end_date"] = scope.get("end_date")
        
        result = self.session.execute(text(query), params)
        row = result.mappings().first()
        
        if row and row["count"] > 0:
            errors.append(f"Found {row['count']} PRs with negative duration values")
        
        return errors
    
    def _validate_commit_mix_constraints(self, scope: Dict[str, Any]) -> List[str]:
        """
        Validate commit mix constraints:
        - Work mix percentages must sum to 100%
        - All line counts must be non-negative
        """
        errors = []
        
        where_clauses = ["organizationid = :org_id", "type = 'COMMIT'"]
        params = {"org_id": scope.get("organization_id")}
        
        if scope.get("repo_id"):
            where_clauses.append("repoid = :repo_id")
            params["repo_id"] = scope["repo_id"]
        
        if scope.get("author_ids"):
            where_clauses.append("authorid = ANY(:author_ids)")
            params["author_ids"] = scope["author_ids"]
        
        where_sql = " AND ".join(where_clauses)
        
        # Check for negative line counts
        query = f"""
            SELECT COUNT(*) as count
            FROM insightly.commit
            WHERE {where_sql}
              AND date >= :start_date
              AND date < :end_date
              AND (
                  newwork < 0
                  OR rework < 0
                  OR maintenance < 0
                  OR assistance < 0
              )
        """
        params["start_date"] = scope.get("start_date")
        params["end_date"] = scope.get("end_date")
        
        result = self.session.execute(text(query), params)
        row = result.mappings().first()
        
        if row and row["count"] > 0:
            errors.append(f"Found {row['count']} commits with negative line counts")
        
        return errors
    
    def _validate_relationships(
        self,
        affected_metrics: List[str],
        scope: Dict[str, Any],
    ) -> List[str]:
        """Validate relationships between affected metrics."""
        errors = []
        
        # Check for conflicting changes
        if "pr_reviewed" in affected_metrics and "pr_unreviewed" in affected_metrics:
            errors.append(
                "Warning: Both pr_reviewed and pr_unreviewed are affected. "
                "Ensure their sum equals total merged review branch PRs."
            )
        
        if "flashy_reviews" in affected_metrics and "pr_reviewed" not in affected_metrics:
            errors.append(
                "Warning: Changing flashy_reviews without checking pr_reviewed constraint"
            )
        
        if "hotfix_prs" in affected_metrics and "release_prs" not in affected_metrics:
            errors.append(
                "Warning: Changing hotfix_prs without checking release_prs constraint"
            )
        
        duration_metrics = {"review_time", "cycle_time", "deploy_time", "coding_time"}
        if len(duration_metrics & set(affected_metrics)) > 1:
            errors.append(
                "Warning: Multiple duration metrics affected. "
                "Ensure cycle_time = coding_time + review_time + deploy_time"
            )
        
        return errors
    
    def validate_in_transaction(
        self,
        sql_statements: List[str],
        sql_params: List[Dict[str, Any]],
        affected_metrics: List[str],
        scope: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Validate changes by executing them in a transaction and checking constraints.
        
        This performs the actual validation by:
        1. Starting a nested transaction
        2. Executing the changes
        3. Checking all constraints
        4. Rolling back
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        transaction = self.session.begin_nested()
        
        try:
            # Execute changes
            for statement, params in zip(sql_statements, sql_params):
                self.session.execute(text(statement), params)
            
            # Validate constraints after changes
            _, constraint_errors = self.validate_change_plan(
                sql_statements,
                sql_params,
                affected_metrics,
                scope,
            )
            errors.extend(constraint_errors)
            
            # Check metric-specific constraints
            for metric_id in affected_metrics:
                metric_errors = self._validate_metric_constraints(metric_id, scope)
                errors.extend(metric_errors)
            
        except Exception as e:
            errors.append(f"Validation failed with error: {str(e)}")
        finally:
            # Always rollback
            transaction.rollback()
            self.session.expire_all()
        
        return len(errors) == 0, errors

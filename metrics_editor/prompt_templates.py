"""
Prompt templates for AI-driven metric changes.

This module provides specialized prompts for different types of metric change requests.
Each template is optimized for a specific category of changes.
"""

from __future__ import annotations

from typing import Dict


class PromptTemplateManager:
    """Manages prompt templates for different change request types."""
    
    def __init__(self):
        self.templates = {
            "commit_volume": self._commit_volume_template(),
            "pr_volume": self._pr_volume_template(),
            "pr_review": self._pr_review_template(),
            "pr_metrics": self._pr_metrics_template(),
            "commit_mix": self._commit_mix_template(),
            "complex": self._complex_template(),
        }
    
    def get_template(self, request_type: str) -> str:
        """Get the appropriate template for a request type."""
        return self.templates.get(request_type, self.templates["complex"])
    
    def _commit_volume_template(self) -> str:
        return """
# Commit Volume Change Request

## User Intent
{user_intent}

## Scope
{scope}

## Current State
{data_context}

## Metrics Context
{metrics_context}

## Constraints
{constraints}

## Your Task
The user wants to modify commit volume or dates. You need to:

1. **Inspect the data**: Use `inspect_commit_data` to understand:
   - How many commits exist in the target period
   - Current date distribution
   - Author distribution
   - Work type breakdown (newwork, rework, maintenance, assistance)

2. **Plan the change**: Determine which commits to modify:
   - If shifting dates: Select commits from source period, calculate delta
   - If changing volume: Decide whether to duplicate or remove commits
   - Consider impact on commit_frequency metric

3. **Validate constraints**:
   - Ensure date shifts maintain chronological order
   - Verify commit work mix percentages remain valid
   - Check that related commit_files records are updated

4. **Generate SQL**: Create UPDATE statements with:
   - Explicit WHERE clauses filtering by scope
   - Parameterized queries for safety
   - Updates to both commit and commit_files tables if needed

5. **Return structured plan** with:
   - sql_statements: List of SQL UPDATE statements
   - parameters: List of parameter dicts matching each statement
   - affected_metrics: ["commit_frequency", "newwork_pct", "rework_pct", "maintenance_pct"]
   - validation_checks: List of constraints you verified
   - reasoning: Explain your approach
   - affected_rows: Estimated number of rows affected

Remember: Commits have related commit_files records that may need date updates too.
"""
    
    def _pr_volume_template(self) -> str:
        return """
# Pull Request Volume Change Request

## User Intent
{user_intent}

## Scope
{scope}

## Current State
{data_context}

## Metrics Context
{metrics_context}

## Constraints
{constraints}

## Your Task
The user wants to modify PR volume or dates. You need to:

1. **Inspect the data**: Use `inspect_pr_data` to understand:
   - How many PRs exist in the target period
   - PR state distribution (OPEN, MERGED, DECLINED)
   - Date fields (createdon, mergedon, approvedon)
   - Related records (pr_reviewer, pr_update, pr_comment)

2. **Plan the change**: Determine which PRs to modify:
   - If shifting open PRs: Update createdon and related timestamps
   - If shifting merged PRs: Update mergedon, approvedon, and related timestamps
   - Calculate date delta from source to target period
   - Consider cascading updates to related tables

3. **Validate constraints**:
   - Ensure createdon < approvedon < mergedon (if applicable)
   - Verify all related records are updated consistently
   - Check that metric formulas remain valid

4. **Generate SQL**: Create UPDATE statements for:
   - insightly.pull_request (main PR record)
   - insightly.pr_reviewer (reviewer records)
   - insightly.pr_update (PR updates)
   - insightly.pr_comment (comments)

5. **Return structured plan** with:
   - sql_statements: List of SQL UPDATE statements
   - parameters: List of parameter dicts
   - affected_metrics: List of impacted metrics (pr_opened, pr_merged, etc.)
   - validation_checks: Constraints verified
   - reasoning: Your approach
   - affected_rows: Estimated rows affected

Remember: PRs have multiple related tables that must be updated atomically.
"""
    
    def _pr_review_template(self) -> str:
        return """
# Pull Request Review Change Request

## User Intent
{user_intent}

## Scope
{scope}

## Current State
{data_context}

## Metrics Context
{metrics_context}

## Constraints
{constraints}

## Your Task
The user wants to modify PR review status or timing. You need to:

1. **Inspect the data**: Use `inspect_pr_data` to understand:
   - Current reviewed vs unreviewed PR counts
   - Review timing distribution (opentoreviewduration)
   - Flashy review counts (< 5 min, > 400 lines)
   - Reviewer assignments

2. **Plan the change**: Determine modifications needed:
   - If marking as reviewed: Set approvedon, approvedby, update durations
   - If marking as unreviewed: Clear approvedon, approvedby, recalculate durations
   - If adjusting review time: Scale opentoreviewduration, update cycle time
   - If changing flashy reviews: Adjust timing or PR size

3. **Validate constraints**:
   - Reviewed + Unreviewed = Total Merged (for review branch PRs)
   - Flashy reviews <= Reviewed PRs
   - Cycle time = Coding time + Review time + Deploy time
   - Review time must be positive and realistic

4. **Generate SQL**: Create UPDATE statements for:
   - insightly.pull_request (approvedon, opentoreviewduration, cycletimeduration, etc.)
   - insightly.pr_reviewer (approved, approveddate)
   - Recalculate dependent duration fields

5. **Return structured plan** with:
   - sql_statements: List of SQL UPDATE statements
   - parameters: List of parameter dicts
   - affected_metrics: ["pr_reviewed", "pr_unreviewed", "flashy_reviews", "review_time", "cycle_time"]
   - validation_checks: Constraints verified
   - reasoning: Your approach
   - affected_rows: Estimated rows affected

Remember: Review changes cascade to cycle time and other duration metrics.
"""
    
    def _pr_metrics_template(self) -> str:
        return """
# Pull Request Metrics Change Request

## User Intent
{user_intent}

## Scope
{scope}

## Current State
{data_context}

## Metrics Context
{metrics_context}

## Constraints
{constraints}

## Your Task
The user wants to modify PR-related metrics (size, timing, flags). You need to:

1. **Inspect the data**: Use `inspect_pr_data` to understand:
   - PR size distribution (linesadded, linesremoved)
   - Duration fields (cycletimeduration, deploytimeduration, committoopenduration)
   - Boolean flags (releasebranchpr, hotfixpr, reviewbranchpr)
   - Current metric values

2. **Plan the change**: Determine modifications needed:
   - If changing PR size: Update linesadded/linesremoved
   - If scaling durations: Multiply duration fields by scale factor
   - If toggling flags: Set boolean fields, verify constraints
   - Consider impact on dependent metrics

3. **Validate constraints**:
   - Hotfix PRs <= Release PRs
   - Cycle time = Coding time + Review time + Deploy time (recalculate if needed)
   - PR size changes may affect large_prs and flashy_reviews metrics
   - Duration scaling must preserve metric relationships

4. **Generate SQL**: Create UPDATE statements for:
   - insightly.pull_request (target columns)
   - Recalculate dependent fields if necessary

5. **Return structured plan** with:
   - sql_statements: List of SQL UPDATE statements
   - parameters: List of parameter dicts
   - affected_metrics: List of impacted metrics
   - validation_checks: Constraints verified
   - reasoning: Your approach
   - affected_rows: Estimated rows affected

Remember: Many PR fields are interdependent and must be updated consistently.
"""
    
    def _commit_mix_template(self) -> str:
        return """
# Commit Work Mix Change Request

## User Intent
{user_intent}

## Scope
{scope}

## Current State
{data_context}

## Metrics Context
{metrics_context}

## Constraints
{constraints}

## Your Task
The user wants to modify the distribution of work types in commits. You need to:

1. **Inspect the data**: Use `inspect_commit_data` to understand:
   - Current work type distribution (newwork, rework, maintenance, assistance)
   - Total lines per commit
   - Current percentages

2. **Plan the change**: Determine modifications needed:
   - Calculate new line counts based on target percentages
   - Ensure percentages sum to 100%
   - Preserve total lines per commit
   - Distribute lines according to new ratios

3. **Validate constraints**:
   - newwork_pct + rework_pct + maintenance_pct + assistance_pct = 100%
   - All percentages >= 0 and <= 100
   - Total lines remain unchanged per commit
   - Line counts are non-negative integers

4. **Generate SQL**: Create UPDATE statement:
   - Calculate new line counts: newwork = ROUND(total_lines * newwork_pct / 100.0)
   - Handle rounding to ensure sum equals total
   - Use explicit WHERE clause for scope

5. **Return structured plan** with:
   - sql_statements: List of SQL UPDATE statements
   - parameters: List of parameter dicts
   - affected_metrics: ["newwork_pct", "rework_pct", "maintenance_pct"]
   - validation_checks: Constraints verified
   - reasoning: Your approach
   - affected_rows: Estimated rows affected

Remember: Work mix percentages must always sum to 100% after changes.
"""
    
    def _complex_template(self) -> str:
        return """
# Complex Multi-Metric Change Request

## User Intent
{user_intent}

## Scope
{scope}

## Current State
{data_context}

## Metrics Context
{metrics_context}

## Constraints
{constraints}

## Your Task
The user has a complex request that may affect multiple metrics. You need to:

1. **Understand the request**: Break down the user's intent into:
   - Primary metrics to change
   - Secondary metrics that will be affected
   - Dependencies between metrics
   - Constraints that must be preserved

2. **Inspect the data**: Use available tools to understand:
   - Current state of all relevant metrics
   - Data distribution and patterns
   - Relationships between tables
   - Potential conflicts or constraints

3. **Plan the change**: Create a coordinated plan:
   - Order changes to respect dependencies
   - Ensure all constraints are maintained
   - Validate that changes are internally consistent
   - Consider cascading effects

4. **Validate constraints**: Use `validate_metric_impact` to check:
   - All metric formulas remain valid
   - No constraint violations
   - Changes are realistic and achievable
   - Dependencies are preserved

5. **Generate SQL**: Create a sequence of UPDATE statements:
   - Order statements to respect dependencies
   - Use explicit WHERE clauses
   - Include all necessary table updates
   - Recalculate dependent fields

6. **Return structured plan** with:
   - sql_statements: Ordered list of SQL UPDATE statements
   - parameters: List of parameter dicts
   - affected_metrics: Complete list of impacted metrics
   - validation_checks: All constraints verified
   - reasoning: Detailed explanation of your approach
   - affected_rows: Estimated rows affected

Remember: Complex changes require careful coordination to maintain data integrity.
"""

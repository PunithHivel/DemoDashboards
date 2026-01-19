"""
AI Orchestrator for metric changes.

This module provides AI-driven metric change planning using OpenAI with MCP tool access.
It translates user intent into structured database modifications while preserving metric
dependencies and data consistency.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import openai
from sqlalchemy.orm import Session

from metrics_editor.catalog import load_catalog
from metrics_editor.models import (
    AIChangeRequest,
    AIChangePlan,
    MetricScope,
    ChangePlan,
)
from metrics_editor.mcp_tools import MCPToolRegistry
from metrics_editor.prompt_templates import PromptTemplateManager
from metrics_editor.validators import MetricValidator


class AIOrchestrator:
    """
    Orchestrates AI-driven metric changes.
    
    This class:
    1. Accepts natural language change requests from users
    2. Translates them into structured prompts with context
    3. Provides MCP tools to AI for database inspection
    4. Validates AI-generated plans against metric constraints
    5. Returns safe, executable SQL plans
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.mcp_registry = MCPToolRegistry(session)
        self.prompt_manager = PromptTemplateManager()
        self.validator = MetricValidator(session)
        self.catalog = load_catalog()
        
    def process_change_request(
        self,
        request: AIChangeRequest,
    ) -> AIChangePlan:
        """
        Process a natural language change request.
        
        Args:
            request: User's change request with intent and scope
            
        Returns:
            AIChangePlan with SQL statements and validation results
            
        Raises:
            ValueError: If the request cannot be fulfilled safely
        """
        # Step 1: Classify the request type
        request_type = self._classify_request(request.user_intent)
        
        # Step 2: Build context-aware prompt
        prompt = self._build_prompt(request, request_type)
        
        # Step 3: Get available MCP tools for the AI
        tools = self._get_mcp_tools()
        
        # Step 4: Call OpenAI with function calling
        ai_response = self._call_openai_with_tools(prompt, tools)
        
        # Step 5: Parse AI response into structured plan
        raw_plan = self._parse_ai_response(ai_response)
        
        # Step 6: Validate the plan against constraints
        validated_plan = self._validate_plan(raw_plan, request.scope)
        
        # Step 7: Build final change plan
        return self._build_change_plan(validated_plan, request)
    
    def _classify_request(self, user_intent: str) -> str:
        """
        Classify the type of change request.
        
        Returns one of:
        - "commit_volume": Change commit counts or dates
        - "pr_volume": Change PR counts or dates
        - "pr_review": Modify review status or timing
        - "pr_metrics": Adjust PR-related metrics (size, timing)
        - "commit_mix": Adjust work type distribution
        - "complex": Multi-metric change requiring coordination
        """
        classification_prompt = f"""
Classify this metric change request into one category:

User request: "{user_intent}"

Categories:
- commit_volume: Changing commit counts or shifting commit dates
- pr_volume: Changing PR counts or shifting PR dates
- pr_review: Modifying review status, review time, or reviewer data
- pr_metrics: Adjusting PR size, cycle time, deploy time, or flags
- commit_mix: Adjusting work type distribution (new work, rework, maintenance)
- complex: Multi-metric changes or unclear intent

Return ONLY the category name, nothing else.
"""
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": classification_prompt}],
            temperature=0,
        )
        
        return response.choices[0].message.content.strip()
    
    def _build_prompt(self, request: AIChangeRequest, request_type: str) -> str:
        """Build a context-aware prompt for the AI."""
        # Get the appropriate template
        template = self.prompt_manager.get_template(request_type)
        
        # Get metric catalog context
        metrics_context = self._build_metrics_context(request.scope)
        
        # Get current data snapshot
        data_context = self._build_data_context(request.scope)
        
        # Build the full prompt
        prompt = template.format(
            user_intent=request.user_intent,
            scope=self._format_scope(request.scope),
            metrics_context=metrics_context,
            data_context=data_context,
            constraints=self._build_constraints_context(),
        )
        
        return prompt
    
    def _build_metrics_context(self, scope: MetricScope) -> str:
        """Build context about available metrics and their dependencies."""
        metrics = self.catalog.get("metrics", [])
        
        context_lines = ["Available metrics and their dependencies:"]
        for metric in metrics:
            affects = metric.get("affects", [])
            context_lines.append(
                f"- {metric['id']} ({metric['label']}): "
                f"affects {', '.join(affects) if affects else 'none'}"
            )
        
        return "\n".join(context_lines)
    
    def _build_data_context(self, scope: MetricScope) -> str:
        """Build context about current data state."""
        # Use MCP tools to get current state
        context_lines = ["Current data state:"]
        
        # Get PR counts
        pr_summary = self.mcp_registry.get_pr_summary(scope)
        context_lines.append(f"- Total PRs: {pr_summary.get('total', 0)}")
        context_lines.append(f"- Merged PRs: {pr_summary.get('merged', 0)}")
        context_lines.append(f"- Reviewed PRs: {pr_summary.get('reviewed', 0)}")
        context_lines.append(f"- Unreviewed PRs: {pr_summary.get('unreviewed', 0)}")
        
        # Get commit counts
        commit_summary = self.mcp_registry.get_commit_summary(scope)
        context_lines.append(f"- Total commits: {commit_summary.get('total', 0)}")
        
        return "\n".join(context_lines)
    
    def _build_constraints_context(self) -> str:
        """Build context about constraints that must be preserved."""
        return """
Critical constraints:
1. Reviewed PRs + Unreviewed PRs = Total Merged PRs (for review branch PRs)
2. Flashy reviews <= Reviewed PRs
3. Hotfix PRs <= Release PRs
4. Cycle time = Coding time + Review time + Deploy time
5. All date shifts must maintain chronological order
6. Commit work mix percentages must sum to 100%
7. Cannot create data that violates foreign key constraints
8. Changes must be realistic and internally consistent
"""
    
    def _format_scope(self, scope: MetricScope) -> str:
        """Format scope information for the prompt."""
        parts = [
            f"Organization: {scope.organization_id}",
            f"Date range: {scope.start_date} to {scope.end_date}",
        ]
        if scope.repo_id:
            parts.append(f"Repository: {scope.repo_id}")
        if scope.team_id:
            parts.append(f"Team: {scope.team_id}")
        if scope.author_ids:
            parts.append(f"Authors: {', '.join(map(str, scope.author_ids))}")
        return "\n".join(parts)
    
    def _get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Get MCP tools formatted for OpenAI function calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "inspect_pr_data",
                    "description": "Inspect pull request data for the given scope",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filters": {
                                "type": "object",
                                "description": "Filters to apply (state, date range, etc.)",
                            },
                            "columns": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Columns to retrieve",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Max rows to return",
                            },
                        },
                        "required": ["filters"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "inspect_commit_data",
                    "description": "Inspect commit data for the given scope",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filters": {
                                "type": "object",
                                "description": "Filters to apply (date range, type, etc.)",
                            },
                            "columns": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Columns to retrieve",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Max rows to return",
                            },
                        },
                        "required": ["filters"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "validate_metric_impact",
                    "description": "Validate how a change would impact related metrics",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "metric_id": {
                                "type": "string",
                                "description": "The metric being changed",
                            },
                            "proposed_change": {
                                "type": "object",
                                "description": "Description of the proposed change",
                            },
                        },
                        "required": ["metric_id", "proposed_change"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_metric_formula",
                    "description": "Get the formula and dependencies for a metric",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "metric_id": {
                                "type": "string",
                                "description": "The metric ID",
                            },
                        },
                        "required": ["metric_id"],
                    },
                },
            },
        ]
    
    def _call_openai_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Call OpenAI with function calling enabled."""
        messages = [
            {
                "role": "system",
                "content": """You are an expert database engineer specializing in metric manipulation.
Your task is to generate safe SQL statements that modify database records to achieve
the user's desired metric changes while preserving all constraints and dependencies.

You have access to tools to inspect the database and validate your changes.
Use them to understand the current state before proposing modifications.

Always:
1. Inspect current data before planning changes
2. Validate that changes preserve metric formulas
3. Check that constraints are maintained
4. Generate parameterized SQL with explicit WHERE clauses
5. Explain your reasoning

Return your final plan as a JSON object with:
- sql_statements: List of SQL UPDATE/INSERT statements
- parameters: List of parameter dicts for each statement
- affected_rows: Estimated rows affected
- validation_checks: List of constraints verified
- reasoning: Explanation of your approach
""",
            },
            {"role": "user", "content": prompt},
        ]
        
        # Initial call
        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0,
        )
        
        # Handle tool calls iteratively
        while response.choices[0].message.tool_calls:
            messages.append(response.choices[0].message)
            
            for tool_call in response.choices[0].message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Execute the tool
                tool_result = self._execute_mcp_tool(function_name, function_args)
                
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result),
                    }
                )
            
            # Get next response
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0,
            )
        
        # Extract final response
        final_content = response.choices[0].message.content
        
        return {
            "content": final_content,
            "messages": messages,
        }
    
    def _execute_mcp_tool(
        self,
        function_name: str,
        function_args: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute an MCP tool and return results."""
        if function_name == "inspect_pr_data":
            return self.mcp_registry.inspect_pr_data(**function_args)
        elif function_name == "inspect_commit_data":
            return self.mcp_registry.inspect_commit_data(**function_args)
        elif function_name == "validate_metric_impact":
            return self.mcp_registry.validate_metric_impact(**function_args)
        elif function_name == "get_metric_formula":
            return self.mcp_registry.get_metric_formula(**function_args)
        else:
            return {"error": f"Unknown tool: {function_name}"}
    
    def _parse_ai_response(self, ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the AI's response into a structured plan."""
        content = ai_response["content"]
        
        # Try to extract JSON from the response
        try:
            # Look for JSON block
            if "```json" in content:
                json_start = content.index("```json") + 7
                json_end = content.index("```", json_start)
                json_str = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.index("```") + 3
                json_end = content.index("```", json_start)
                json_str = content[json_start:json_end].strip()
            else:
                json_str = content
            
            plan = json.loads(json_str)
            return plan
        except (ValueError, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to parse AI response as JSON: {e}\nContent: {content}")
    
    def _validate_plan(
        self,
        raw_plan: Dict[str, Any],
        scope: MetricScope,
    ) -> Dict[str, Any]:
        """
        Validate the AI-generated plan against constraints.
        
        This performs safety checks:
        1. SQL statements are valid UPDATE/INSERT only (no DELETE/DROP)
        2. All statements have WHERE clauses
        3. Metric constraints are preserved
        4. No orphaned records created
        """
        validated = raw_plan.copy()
        warnings = []
        
        sql_statements = validated.get("sql_statements", [])
        sql_params = validated.get("parameters", [])
        affected_metrics = validated.get("affected_metrics", [])
        
        # Convert scope to dict for validator
        scope_dict = {
            "organization_id": scope.organization_id,
            "repo_id": scope.repo_id,
            "team_id": scope.team_id,
            "author_ids": scope.author_ids,
            "start_date": scope.start_date,
            "end_date": scope.end_date,
        }
        
        # Use the validator to check the plan
        is_valid, errors = self.validator.validate_change_plan(
            sql_statements,
            sql_params,
            affected_metrics,
            scope_dict,
        )
        
        if not is_valid:
            raise ValueError(f"Plan validation failed:\n" + "\n".join(f"- {e}" for e in errors))
        
        # Add any validation warnings
        warnings.extend([e for e in errors if e.startswith("Warning:")])
        
        # Validate constraints
        validation_checks = validated.get("validation_checks", [])
        if not validation_checks:
            warnings.append("No validation checks provided by AI")
        
        # Perform in-transaction validation
        tx_valid, tx_errors = self.validator.validate_in_transaction(
            sql_statements,
            sql_params,
            affected_metrics,
            scope_dict,
        )
        
        if not tx_valid:
            raise ValueError(
                f"Transaction validation failed:\n" + "\n".join(f"- {e}" for e in tx_errors)
            )
        
        validated["warnings"] = warnings
        return validated
    
    def _build_change_plan(
        self,
        validated_plan: Dict[str, Any],
        request: AIChangeRequest,
    ) -> AIChangePlan:
        """Build the final change plan."""
        from metrics_editor.storage import create_plan_id
        
        return AIChangePlan(
            plan_id=create_plan_id(),
            user_intent=request.user_intent,
            request_type=validated_plan.get("request_type", "ai_driven"),
            sql_statements=validated_plan.get("sql_statements", []),
            sql_params=validated_plan.get("parameters", []),
            affected_metrics=validated_plan.get("affected_metrics", []),
            validation_checks=validated_plan.get("validation_checks", []),
            reasoning=validated_plan.get("reasoning", ""),
            estimated_rows=validated_plan.get("affected_rows", 0),
            warnings=validated_plan.get("warnings", []),
        )

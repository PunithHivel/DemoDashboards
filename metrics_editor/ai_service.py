"""
Simplified AI Service for metric changes.

This service takes filtered data and user request, sends to OpenAI,
and returns structured JSON that the backend uses to build SQL.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List

import openai
from jinja2 import Environment, FileSystemLoader


class AIMetricService:
    """
    Simplified AI service that takes filtered data and returns JSON for SQL building.
    
    Flow:
    1. Backend filters data based on user's scope
    2. Backend calls this service with filtered data + request
    3. AI analyzes and returns JSON describing what to change
    4. Backend uses JSON to build SQL (via existing playbooks)
    """
    
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Setup Jinja2 environment for prompt templates
        template_dir = Path(__file__).parent / "prompts"
        self.jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))
        self.prompt_template = self.jinja_env.get_template("ai_metric_change.jinja")
        self.metrics_reference = (Path(__file__).parents[1] / "metrics_reference.jinja").read_text(encoding="utf-8")
    
    def generate_change_plan(
        self,
        metric_id: str,
        action: str,
        options: Dict[str, Any],
        filtered_data: List[Dict[str, Any]],
        metric_formulas: Dict[str, str],
        constraints: List[str],
    ) -> Dict[str, Any]:
        """
        Generate a change plan based on filtered data and user request.
        
        Args:
            metric_id: The metric being changed (e.g., "pr_reviewed")
            action: The action to perform (e.g., "set_reviewed_count")
            options: User's options (e.g., {"count": 10, "month": "2025-12"})
            filtered_data: Pre-filtered data from database
            metric_formulas: How metrics are calculated
            constraints: Constraints that must be preserved
            
        Returns:
            JSON dict with:
            - selected_record_ids: List of IDs to modify
            - field_updates: Dict of field -> value/expression
            - reasoning: Explanation of the plan
            - validation_notes: Any warnings or notes
        """
        # Build prompt for AI
        prompt = self._build_prompt(
            metric_id,
            action,
            options,
            filtered_data,
            metric_formulas,
            constraints,
        )
        
        # Debug: Log key parts of the prompt
        print(f"[AI Service] Sending to OpenAI:")
        print(f"  - Action: {action}")
        print(f"  - Options: {options}")
        print(f"  - Total records: {len(filtered_data)}")
        print(f"  - Prompt length: {len(prompt)} chars")
        
        # Call OpenAI
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": self._get_system_prompt(),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        
        # Parse response
        content = response.choices[0].message.content
        result = json.loads(content)
        
        # Debug: Log AI response
        print(f"[AI Service] Received from OpenAI:")
        print(f"  - Selected records: {len(result.get('selected_record_ids', []))}")
        print(f"  - Reasoning preview: {result.get('reasoning', 'N/A')[:150]}...")
        
        return result
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt that defines AI's role."""
        return """You are an expert database analyst helping to modify metrics data.

Your task is to analyze the user's request and ALL the filtered data provided, then return a JSON plan
that describes EXACTLY WHAT to change (not HOW - the backend will build the SQL).

You will receive ALL the filtered records (not just samples). You must:
1. Analyze ALL the records provided
2. Decide which specific records need to be changed based on the user's requirements
3. Return the exact list of record IDs that should be modified

You must return a JSON object with this structure:
{
  "selected_record_ids": [list of IDs to modify - be precise and complete],
  "field_updates": {
    "field_name": "value or expression"
  },
  "reasoning": "Clear explanation of your selection logic and why you chose these specific records",
  "validation_notes": ["any warnings or notes"],
  "estimated_impact": {
    "records_affected": number,
    "metrics_affected": ["list of metric IDs"]
  }
}

Important rules:
1. You receive ALL filtered records - analyze them completely
2. Select the exact records that match the user's requirements
3. Respect all constraints provided
4. If user asks for 10 records, select exactly 10 (or explain why less)
5. Explain your reasoning clearly - which records and why
6. Note any potential issues or warnings
7. Return ONLY valid JSON, no additional text"""
    
    def _build_prompt(
        self,
        metric_id: str,
        action: str,
        options: Dict[str, Any],
        filtered_data: List[Dict[str, Any]],
        metric_formulas: Dict[str, str],
        constraints: List[str],
    ) -> str:
        """Build the user prompt with all context using Jinja2 template."""
        
        # Summarize data
        data_summary = self._summarize_data(filtered_data, action)
        
        # Format ALL records (not just samples)
        all_records = self._format_all_records(filtered_data)
        
        # Render the prompt using Jinja2 template
        prompt = self.prompt_template.render(
            metric_id=metric_id,
            action=action,
            options=options,
            data_summary=data_summary,
            all_records=all_records,
            total_records=len(filtered_data),
            metric_formulas=self._format_metric_formulas(metric_formulas),
            constraints=self._format_constraints(constraints),
            metrics_reference=self.metrics_reference,
        )
        
        return prompt
    
    def _summarize_data(self, filtered_data: List[Dict[str, Any]], action: str) -> str:
        """Summarize the filtered data for the AI."""
        if not filtered_data:
            return "No records found matching the filters."
        
        total = len(filtered_data)
        summary_lines = [f"Total records: {total}"]
        
        # Action-specific summaries
        if action in ["set_reviewed_count", "set_unreviewed_count"]:
            reviewed = sum(1 for r in filtered_data if r.get("approvedon") is not None)
            unreviewed = total - reviewed
            summary_lines.append(f"- Reviewed: {reviewed}")
            summary_lines.append(f"- Unreviewed: {unreviewed}")
        
        elif action in ["shift_open_prs", "shift_merged_prs"]:
            states = {}
            for r in filtered_data:
                state = r.get("state", "UNKNOWN")
                states[state] = states.get(state, 0) + 1
            for state, count in states.items():
                summary_lines.append(f"- {state}: {count}")
        
        elif action == "set_flashy_reviews":
            flashy = sum(
                1 for r in filtered_data
                if r.get("opentoreviewduration", 999) < 5
                and (r.get("linesadded", 0) + r.get("linesremoved", 0)) > 400
            )
            summary_lines.append(f"- Already flashy: {flashy}")
            summary_lines.append(f"- Can be made flashy: {total - flashy}")
        
        elif action == "set_large_prs":
            large = sum(
                1 for r in filtered_data
                if (r.get("linesadded", 0) + r.get("linesremoved", 0)) > 400
            )
            small = total - large
            summary_lines.append(f"- Large (>400 lines): {large}")
            summary_lines.append(f"- Small (≤400 lines): {small}")
        
        return "\n".join(summary_lines)
    
    def _format_all_records(self, filtered_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format ALL records for the prompt, converting datetime objects to strings and keeping only essential fields."""
        # Essential fields that are always needed
        essential_fields = {
            'id', 'createdon', 'state', 'authorid', 'repoid',
            'approvedon', 'approvedby', 'mergedon', 'updatedon',
            'linesadded', 'linesremoved', 'opentoreviewduration',
            'cycletimeduration', 'deploytimeduration', 'committoopenduration',
            'releasebranchpr', 'hotfixpr', 'flashyreviewedpr', 'reviewbranchpr',
            'date', 'newwork', 'rework', 'maintenance', 'assistance',
            'pr_update_count', 'pr_comment_count', 'pr_reviewer_count',
            'commit_files_count',
        }
        
        return [self._serialize_record(record, essential_fields) for record in filtered_data]
    
    def _serialize_record(self, record: Dict[str, Any], essential_fields: set = None) -> Dict[str, Any]:
        """Convert datetime objects to strings for JSON serialization, keeping only essential fields."""
        serialized = {}
        for key, value in record.items():
            # Skip non-essential fields if specified
            if essential_fields and key not in essential_fields:
                continue
                
            if isinstance(value, (datetime, date)):
                serialized[key] = value.isoformat()
            elif value is None:
                serialized[key] = None
            else:
                serialized[key] = value
        return serialized
    
    def _format_metric_formulas(self, metric_formulas: Dict[str, str]) -> str:
        """Format metric formulas for the prompt."""
        if not metric_formulas:
            return "No formulas provided."
        
        lines = []
        for metric_id, formula in metric_formulas.items():
            lines.append(f"- {metric_id}: {formula}")
        return "\n".join(lines)
    
    def _format_constraints(self, constraints: List[str]) -> str:
        """Format constraints for the prompt."""
        if not constraints:
            return "No specific constraints."
        
        return "\n".join(f"- {c}" for c in constraints)

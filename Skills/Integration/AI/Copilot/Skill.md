---
name: demodashboards-integration-ai-copilot
description: Generate or maintain Copilot integration data patterns for DemoDashboards. Use when tasks involve Copilot usage metrics, summaries, dimensions, or provider-specific data preparation.
---

# AI Integration Skill (Copilot, Detailed)

## Objective
Generate complete Copilot datasets so both summary and dimension endpoints return realistic non-null results.

## 1) Table Inventory

### User-level fact table (primary)
- `insightly.github_copilot_user_daily_usage`

### Workspace/team summary tables (optional but common)
- `insightly.copilot_daily_summary`
- `insightly.copilot_editor_usage`
- `insightly.copilot_language_usage`
- `insightly.copilot_seat_usage`
- `insightly.copilot_seat_summary`
- `insightly.copilot_dotcom_chat`
- `insightly.copilot_team`
- `insightly.copilot_team_daily_summary`
- `insightly.copilot_team_language_usage`
- `insightly.copilot_team_status`
- `insightly.copilot_workspace_status`

### Mapping tables
- `insightly.author`
- `insightly.teamauthorrelation`
- `insightly.team`
- `insightly.user_integration_details`

## 2) Table Relationships (ER-style text)
- User daily row joins to team via `author_id -> teamauthorrelation.authorid`.
- Integration scoping uses `organization_id + user_integration_id`.
- Workspace/team summary tables must reconcile with user-level totals for same period.

## 3) Metric Dependencies
- Suggestion acceptance rate:
  - `sum(code_acceptance_activity_count) / sum(code_generation_activity_count)`
- LOC acceptance rate:
  - `(sum(loc_added_sum)+sum(loc_deleted_sum)) / (sum(loc_suggested_to_add_sum)+sum(loc_suggested_to_delete_sum))`
- Adoption:
  - distinct `author_id` using rows in period/team scope
- Dimension metrics require valid JSON arrays in:
  - `totals_by_feature`
  - `totals_by_language_model`
  - `totals_by_language_feature`
  - `totals_by_model_feature`
  - `totals_by_ide`

## 4) Dynamic Data Generation Rules
1. Generate user-level table first; derive summaries from it.
2. Keep all acceptance and LOC counters coherent (accepted <= suggested/generated).
3. Never leave required dimension JSON null for periods expected in UI.
4. Respect team-author membership by usage day.
5. Keep org/integration identifiers consistent across all Copilot tables.
6. Use idempotent upsert keys (`org + usage_day + author + integration`).

## 5) Script Design Pattern
- Section 1: Validation (mapping, denominator presence, JSON readiness)
- Section 2: Insert/Update (user-level + required summaries)
- Section 3: Post-check (rates + dimension payload integrity)

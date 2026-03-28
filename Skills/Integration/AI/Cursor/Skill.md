---
name: demodashboards-integration-ai-cursor
description: Generate or maintain Cursor integration data patterns for DemoDashboards. Use when tasks involve Cursor AI usage, generated-code analytics, or team-level provider metrics.
---

# AI Integration Skill (Cursor)

## Objective
Generate Cursor usage data with valid author/team mapping so AI-generated-code and usage metrics are visible in overview and team analytics.

## 1) Table Inventory

### Primary fact tables
- `insightly.cursor_daily_usage`

### Supporting tables
- `insightly.cursor_initial_sync`
- `insightly.cursor_chunk_sync_process`
- `insightly.cursor_spending` (if spend/cost analytics are enabled)
- `insightly.author`
- `insightly.teamauthorrelation`
- `insightly.team`
- `insightly.user_integration_details`

## 2) Table Relationships (ER-style text)
- `cursor_daily_usage.author_id` maps to source/team author IDs in `teamauthorrelation.authorid`
- `organization_id + user_integration_id` identifies integration ownership scope
- team-level rollups join daily rows to team via author membership by date

## 3) Metric Dependencies
- `AI_GENERATED_CODE`-style rate:
  - numerator: `accepted_lines_added + accepted_lines_deleted`
  - denominator: `total_lines_added + total_lines_deleted`
- Active user/adoption: distinct `author_id` / `email`
- request/tool usage: request and usage counters in `cursor_daily_usage`

## 4) Dynamic Data Generation Rules
1. Generate author-mapped daily rows first (`cursor_daily_usage`).
2. Keep acceptance <= total at line and action levels.
3. Maintain date continuity for the requested window.
4. Keep `organization_id`, `user_integration_id`, `author_id` consistent with integration mapping.
5. Use idempotent upsert keys: `(organization_id, date, author_id, user_integration_id)`.

## 5) Script Design Pattern
- Section 1: Validation (mapping + denominator readiness)
- Section 2: Insert/Update (daily usage + optional spend/sync support)
- Section 3: Post-check (AI generated code rate + active users)

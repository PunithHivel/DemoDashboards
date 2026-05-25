---
name: demodashboards-integration-ai-claude
description: Generate or maintain Claude integration data patterns for DemoDashboards. Use when tasks involve Claude usage metrics, adoption analytics, or provider-specific data preparation.
---

# AI Integration Skill (Claude)

## Objective
Generate Claude usage data that maps cleanly to team/source authors and supports dashboard/adoption metrics.

## 1) Table Inventory

### Primary fact tables
- `insightly.claude_code_report`

### Supporting tables
- `insightly.author` (provider identity + `assignedauthorid`)
- `insightly.teamauthorrelation`
- `insightly.team`
- `insightly.user_integration_details` (integration ownership)
- `insightly.claude_code_initial_sync` / `insightly.claude_code_api_key` (if used in environment)

## 2) Table Relationships (ER-style text)
- Claude provider author (`scmprovider='claudecode`) links to source Git author via `author.assignedauthorid`
- Team membership is driven by source author IDs in `teamauthorrelation`
- `claude_code_report.author_id` should point to source/team-mapped author where dashboards expect team rollups
- `claude_code_report.originalauthorid` keeps provider-side author identity

## 3) Metric Dependencies
- Adoption/active users: distinct author/user counts from `claude_code_report`
- Acceptance metrics: accepted vs rejected tool fields
- Productivity: `lines_added`, `lines_removed`, `commits_by_claude_code`, `pull_requests_by_claude_code`
- Model/token cost views: `model_breakdown` JSON

## 4) Dynamic Data Generation Rules
1. **Author mapping first**:
   - Resolve provider author -> source author mapping before report inserts.
2. **Keep JSON valid**:
   - `model_breakdown` must be valid JSON array when token/cost charts are expected.
3. **Date continuity**:
   - Generate daily rows across requested period; avoid sparse gaps unless intentionally modeled.
4. **Acceptance coherence**:
   - accepted + rejected counts must remain internally consistent by tool type.
5. **Idempotent writes**:
   - upsert by `(organization_id, date, author_id, originalauthorid)` where possible.

## 5) Script Design Pattern
- Section 1: Validation (author mapping, integration IDs)
- Section 2: Insert/Update (report rows)
- Section 3: Post-check (active users, acceptance, lines)

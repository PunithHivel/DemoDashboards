---
name: demodashboards-integration-jira
description: Generate or maintain Jira integration data workflows for DemoDashboards. Use when tasks involve issues, boards, sprints, completion, throughput, or project analytics.
---

# Jira Integration Skill

## Objective
Generate Jira data so completion, throughput, and board/sprint analytics behave exactly like production joins.

## 1) Table Inventory

### Primary fact tables
- `insightly_jira.issue`
- `insightly_jira.sprint`
- `insightly_jira.board`

### Mapping / support tables
- `insightly_jira.sprint_issue_mapping`
- `insightly_jira.jira_sub_board`
- `insightly_jira.issue_event_log`
- `insightly_jira.issue_hierarchy`
- `insightly.team_board_mapping`
- `insightly.author` (Jira identities mapped via assignedauthorid)
- `insightly.teamauthorrelation`

### Optional hierarchy/custom-field tables
- issue hierarchy fields in `insightly_jira.issue` (`epic_id`, `feature_id`, `initiative_id`, `custom_fields`)

## 2) Table Relationships (ER-style text)
- `board (1) -> (N) sprint` via `sprint.board_id`
- `sprint (1) -> (N) issue` via `issue.sprint_id`
- `board (1) -> (N) issue` via `issue.board_id`
- `sprint (N) <-> (N) issue` via `sprint_issue_mapping`
- `board (1) -> (N) jira_sub_board`
- `issue (1) -> (N) issue_event_log` via `issue_event_log.issue_id`
- `sprint (1) -> (N) issue_event_log` via `issue_event_log.sprint_id`
- `issue (1) -> (N) issue_hierarchy` via `issue_hierarchy.issue_id`
- `team (N) <-> (N) board` via `team_board_mapping`
- `issue.assignee_id` must resolve to team author scope for team metrics

## 3) Metric Dependencies
- `COMPLETED_ISSUE_COUNT`: `issue` completion status/date logic
- `COMPLETED_STORY_POINTS`: `issue.story_point` with same completion filter
- Completion date logic typically uses `resolution_date`, fallback `status_change_date` for done/closed states
- Sprint hygiene / timeline views also depend on `issue_event_log` and sprint mappings.

## 4) Dynamic Data Generation Rules
1. **Generate board/sprint context first** (board -> sprint -> issue).
2. **Populate both direct and mapping links**:
   - Keep `issue.board_id`, `issue.sprint_id`, and `sprint_issue_mapping` consistent.
   - Keep `issue_event_log` consistent with issue/sprint/board ids.
3. **Status timeline realism**:
   - Keep `jira_create_date <= status_change_date <= resolution_date` when resolved.
4. **Team rollup consistency**:
   - Ensure assignee mapping is valid for target team scope.
5. **Soft-delete behavior**:
   - Keep `is_deleted=false` for active analytical rows.
6. **Idempotent writes**:
   - Use stable natural keys (`org_id + issue_id/key`).

## 5) Script Design Pattern
- Section 1: Validation (board/sprint/issue integrity)
- Section 2: Insert/Update (issues + mappings)
- Section 3: Post-check (completed issues/story points by month/team)

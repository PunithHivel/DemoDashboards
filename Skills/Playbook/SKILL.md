---
name: demodashboards-generation-playbook
description: End-to-end execution playbook for DemoDashboards data generation work. Use this first for new developers/LLMs to follow start-to-end flow with required files, validation order, and handoff outputs.
---

# DemoDashboards Generation Playbook

## Goal
Provide a deterministic, repeatable workflow for generating and validating demo data across Git, Jira, DORA, and AI integrations.

## Start Here (Read Order)
1. `Skills/DataCreation/SKILL.md`
2. `Skills/ScriptCreation/SKILL.md`
3. Integration skills:
   - `Skills/Integration/Git/SKILL.md`
   - `Skills/Integration/Jira/SKILL.md`
   - `Skills/Integration/DORA/SKILL.md`
   - `Skills/Integration/AI/SKILL.md`
4. Metric definitions:
   - `metric_info/Git`
   - `metric_info/jira`
5. Current target dataset:
   - `output/q1_metric_proposals/all_integrations_metrics_q1_proposed_org_6779.csv`

## Execution Flow (Start -> End)
1. **Scope lock**
   - lock org id, team ids, date range, integrations.
   - lock author scope from `teamauthorrelation` + `author`.
2. **Coverage check**
   - list existing org tables/rows from production.
   - identify required child/companion tables, not only top-level facts.
3. **Script build**
   - keep one SQL file per request unless user asks split.
   - include sections:
     - Section 1: Validation/Pre-check
     - Section 2: Fix/Update
     - Section 3: Post-check/Verification
4. **Integration completeness**
   - Git: PR + commit + PR/commit child tables
   - Jira: board/sub-board/sprint/issue + mapping/event/hierarchy
   - DORA: deployments + change requests
   - AI: usage + summary/sync companion tables
5. **ID and relation checks**
   - verify DB-generated ids vs script-generated business ids
   - verify parent->child links (PR id, commit id, sprint/issue ids, summary ids)
6. **Validation**
   - team-level validate scripts first, then global validate.
   - compare against target CSV.
7. **Handoff**
   - update execution report/readme with:
     - tables touched
     - id strategy
     - metric payload and assumptions
     - known caveats and rerun behavior

## Q1'26 Reference Files
- Team generation SQL:
  - `scripts/q126/team_bots/gen_csv.sql`
  - `scripts/q126/team_nova/gen_csv.sql`
  - `scripts/q126/team_phoenix/gen_csv.sql`
  - `scripts/q126/team_vecna/gen_csv.sql`
- Team validation SQL:
  - `scripts/q126/team_bots/validate.sql`
  - `scripts/q126/team_nova/validate.sql`
  - `scripts/q126/team_phoenix/validate.sql`
  - `scripts/q126/team_vecna/validate.sql`
- Global validation:
  - `scripts/q126/validate_q1_2026_vs_csv.sql`
- Report:
  - `scripts/q126/Q1_2026_SQL_EXECUTION_REPORT.md`

## End Criteria
- all required integration tables are populated for scope
- validation output has expected `MATCH/NEAR` profile and no unexplained gaps
- no orphan/invalid ID links in child tables
- report and skills are updated for reproducibility

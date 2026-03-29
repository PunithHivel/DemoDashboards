---
name: data-creation
description: Create or update data generation assets for DemoDashboards. Use when tasks involve preparing seed data, mock datasets, transformation SQL, or sample analytics inputs for this repository.
---

# Data Creation

1. Confirm the request scope and target data format.
2. Generate deterministic, minimal, and valid data artifacts.
3. Keep naming and schema conventions aligned with repository usage.
4. Avoid redundant records or conflicting keys.
5. Validate output shape and basic quality checks before handoff.

## Guided Flow (Start -> End)
1. Read `Skills/Playbook/SKILL.md` first.
2. Read metric definitions:
   - `metric_info/Git`
   - `metric_info/jira`
3. Read target output (if CSV-driven):
   - `output/q1_metric_proposals/all_integrations_metrics_q1_proposed_org_6779.csv`
4. Build/update SQL under requested script folder.
5. Run validation SQL and compare target vs actual.
6. Update execution report/readme for handoff.

## Required Handoff Artifacts
- SQL generation script(s)
- SQL validation script(s)
- execution summary/report with table + ID linkage notes

---
name: demodashboards-script-sql-single-file
description: Enforce SQL script delivery for DemoDashboards. Use when creating or updating SQL scripts in this repo. Produce a single SQL file per request unless the user explicitly asks for multiple files.
---

# DemoDashboards Script Skill

## Start Sequence (Read First)
1. `Skills/Playbook/SKILL.md`
2. `Skills/DataCreation/SKILL.md`
3. Relevant integration skill(s) in `Skills/Integration/*/SKILL.md`
4. Target CSV or metric definition files for the request scope

1. Confirm the task is a SQL script change for this repository.
2. Create exactly one SQL file for the request by default.
3. Do not split into multiple SQL files unless explicitly requested.
4. Keep SQL minimal and non-redundant.
5. Every SQL file must start with a short `What it does` header comment block.
6. In `What it does`, summarize:
   - target metrics/teams/scope,
   - data source rule (existing data only vs synthetic),
   - exactly which tables/columns are updated.
7. Always include explicit section markers in SQL:
   - `Section 1: Validation/Pre-check`
   - `Section 2: Fix/Update`
   - `Section 3: Post-check/Verification`
   - add more only if strictly needed.
8. Before finalizing SQL, perform a table coverage check against production for the target org:
   - list base tables and related/child tables,
   - verify where the org already has rows,
   - include missing but required related tables in the script.
9. For integration data scripts, do not stop at top-level tables:
   - Git: include related PR/commit child tables when applicable.
   - Jira: include board/sprint/mapping/event-log/hierarchy tables when applicable.
   - AI: include provider summary/usage/sync companion tables when applicable.
10. In each SQL file, add a brief `What it does` block that includes:
   - table list touched,
   - ID generation strategy (DB-generated vs script-generated),
   - key table-to-table ID relations.
11. For Qx data-generation scripts, `What it does` must also include explicit payload details:
   - board/sub-board naming pattern and ID strategy,
   - epic strategy (`epic_id` populated or intentionally NULL),
   - issue-type split with counts/percentages,
   - monthly counts at minimum: commits, PRs, issues, and PR-commit assumption,
   - monthly timing targets at minimum: coding/review/merge/deploy time.
12. For Git mapping tables, do not default to 1:1 cardinality:
   - `pr_reviewer`, `pr_comment`, and `pr_update` can have multiple rows per PR.
   - Prefer deterministic per-team/per-month distributions when realism is required.
   - Keep metric-safe behavior (e.g., extra reviewer rows should usually be non-approved).
13. Before adding `pr_commit_relation` or `deployment_pull_requests`, confirm org-specific baseline:
   - if baseline is zero and service metrics do not require them for that scope, keep them unchanged.
   - only insert when source-model parity explicitly requires it.
14. For generated Git textual fields:
   - use realistic deterministic templates for `commit.message` and `pr_comment.text`.
   - avoid static placeholders like repeated `Q126...` text across all rows.

## End Criteria
- SQL sections are complete and ordered.
- Required related tables are included (no top-level-only scripts).
- ID linkages are explicit and consistent across parent/child tables.
- Validation SQL exists and is runnable.
- Handoff report is updated with assumptions and caveats.

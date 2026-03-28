---
name: demodashboards-script-sql-single-file
description: Enforce SQL script delivery for DemoDashboards. Use when creating or updating SQL scripts in this repo. Produce a single SQL file per request unless the user explicitly asks for multiple files.
---

# DemoDashboards Script Skill

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

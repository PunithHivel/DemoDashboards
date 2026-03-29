---
name: demodashboards-integration-git
description: Generate or maintain Git integration data workflows for DemoDashboards. Use when tasks involve repositories, commits, pull requests, author mapping, or team rollup analytics.
---

# Git Integration Skill (Detailed, Dynamic)

## Objective
Generate production-like Git datasets so team/org metrics are computable from real relational paths (author -> team -> repo -> PR/commit) with no broken joins.

## Read Before You Start
1. `Skills/Playbook/SKILL.md`
2. `Skills/ScriptCreation/SKILL.md`
3. `metric_info/Git`
4. current target CSV (if CSV-driven request)

## What This Skill Must Guarantee
- Data is created across **all dependent tables**, not just top-level facts.
- Team rollups work without manual patching.
- Metric denominators are present (avoid null/0-only dashboards unless intentionally modeled).
- Scripts are idempotent and safe for repeated runs.

## 1) Table Inventory

### Core fact tables (required)
- `insightly.pull_request`
- `insightly.commit`
- `insightly.commit_files`
- `insightly.pr_reviewer`
- `insightly.pr_comment`
- `insightly.pr_update`

### Scope/mapping tables (required)
- `insightly.author`
- `insightly.teamauthorrelation`
- `insightly.team`
- `insightly.repo`

### Integration/mapping support (conditional)
- `insightly.user_integration_details`
- `insightly.jira_git_mapping` and correction tables used by this repo

### Deployment-coupled support (required for Deploy/Lead metrics)
- `insightly.deployment_frequency`
- pull-request deployment columns:
  - `is_deployment_pr`
  - `deployment_record_id`
  - `mergetodeployduration`

### PR/commit mapping support (environment dependent)
- `insightly.pr_commit_relation`
- `insightly.deployment_pull_requests`
- Note: for org `6779`, current production baseline has `0` rows in both tables. Do not force insert there unless source pattern changes.

### Optional legacy aggregates (do not treat as primary source)
- `insightly.authoraggregateddata`
- `insightly.repoaggregateddata`

## 2) Relationship Model (ER-style text)
- `team (1) -> (N) teamauthorrelation`
- `author (1) <- (N) teamauthorrelation`
- `author (1) -> (N) pull_request` via `pull_request.authorid`
- `author (1) -> (N) commit` via `commit.authorid`
- `repo (1) -> (N) pull_request` and `repo (1) -> (N) commit` via `repoid`
- `pull_request (1) -> (N) pr_reviewer`
- `pull_request (1) -> (N) pr_comment`
- `pull_request (1) -> (N) pr_update`
- `commit (1) -> (N) commit_files`
- `pull_request (N) <-> (N) commit` through `pr_commit_relation` (if used in that org/environment)
- Provider identities map via `author.assignedauthorid` to source Git author where applicable.

## 3) Metric Dependency Map (Git)

### Speed / Flow
- `REVIEW_TIME`: `pull_request.opentoreviewduration`
- `MERGE_TIME`: `pull_request.deploytimeduration`
- `CODING_TIME`: `pull_request.committoopenduration`
- `CYCLE_TIME`: `pull_request.cycletimeduration`
- `DEPLOY_TIME`: `pull_request.mergetodeployduration`
- `DELIVERY_LEAD_TIME`: `pull_request.cycletimeduration + pull_request.mergetodeployduration`
  - denominator requires deployment linkage conditions in service query

### Quality
- `HOTFIX_RATE`: `hotfixpr=true` over `releasebranchpr=true` denominator
- `FLASHY_REVIEWS`: `flashyreviewedpr=true` over reviewed PR denominator
- `PR_REVIEWED`: approved/reviewed branch denominator logic
- `PR_UNREVIEWED_MERGE`: approved-on-null over review-branch denominator
- `PR_LARGE`: large PR count over opened PR denominator

### Activity / Work split
- `COMMITS`: `commit.type='COMMIT`
- `COMMIT_FREQUENCY`: commits per period/team-author scope
- `NEW_WORK / REWORK / MAINTENANCE`: commit split fields
- `ACTIVE_DAYS`: union of commit dates + PR lifecycle dates + `pr_update.date` activity dates

### Service query dependency notes (insightly-svc)
- Review-count style metrics use `pr_reviewer` with `approved=true` and `approveddate` filters; keep only one approved reviewer row per reviewed PR unless intentionally testing multiple approvals.
- Activity timelines and active days depend on `pr_update`; if adding multiple update rows per PR, keep them on realistic timestamps and avoid invalid ordering.
- `pr_comment` is used in PR detail/comment flows and should align by `pullrequestid`, `organizationid`, `authorid`.
- `pr_commit_relation` is used in report/detail joins in svc, but not all orgs populate it.

## 4) Dynamic Generation Rules (Not Hard-Scoped)
1. Resolve scope dynamically:
   - org -> teams -> active team-author links for requested dates.
2. Build denominator-first:
   - create denominator-eligible rows first (release/review/deployment-linked rows).
3. Use production filters in generation and verification:
   - PR: `excludepr=false`, `autoexcludepr=false`
   - Commit: `skipfromcalculation=false`, `is_auto_excluded=false`
4. Preserve invariants:
   - `PR_REVIEWED + PR_UNREVIEWED_MERGE = 100%`
   - `NEW_WORK + REWORK + MAINTENANCE = 100%`
   - `hotfixpr=true` only for release-eligible PRs
5. Deploy/lead-time readiness:
   - if generating delivery metrics, ensure deployment linkage fields are populated consistently.
6. PR mapping realism:
   - do not assume 1:1 row counts (`PR count == reviewer/comment/update rows`).
   - generate deterministic multi-row distributions for `pr_reviewer` / `pr_comment` / `pr_update` when realism is required.
   - keep metric-safe behavior: extra reviewer rows should generally be `approved=false` to avoid inflating reviewed-PR counts.
7. Time realism:
   - keep timestamp order plausible (`first commit <= open <= review <= approval <= merge <= deploy`).
8. Idempotency:
   - upsert by stable keys (`organizationid + external ids + date/period`), no duplicate facts.

## 5) Script Blueprint (Mandatory)
- Section 1: Validation
  - table coverage, mapping health, denominator presence.
- Section 2: Data Generation / Fix
  - scoped inserts/updates only; no unrelated table mutation.
- Section 3: Post-check
  - recompute target metrics exactly with service-like filters.

## 6) Correlation Rules for Realistic Output
- Higher commit throughput should generally coincide with:
  - higher PR volume and non-zero review denominator.
- If Delivery Lead Time is expected non-null:
  - deployment-linked PR denominator must exist.
- Hotfix spikes should be rare unless simulating incidents.
- Flashy review rate should remain small unless intentionally testing bad-review scenarios.

## 7) Common Failure Modes and Fix Order
1. Missing team metric -> check denominator first.
2. Denominator exists but metric null -> check mapping/flag columns.
3. Deployment metrics null -> check `deployment_record_id` + `is_deployment_pr` + `mergetodeployduration`.
4. Reviewer metrics off -> check `reviewbranchpr`, `approvedon`, `pr_reviewer` consistency.

## End Checklist
- PR/commit parent-child links verified.
- team-author-org scope verified.
- denominator coverage verified for hotfix/review/release/deploy metrics.
- post-check query output documented.

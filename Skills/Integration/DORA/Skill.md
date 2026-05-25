---
name: demodashboards-integration-dora
description: Generate or maintain DORA integration data workflows for DemoDashboards. Use when tasks involve deployment frequency, lead time, change failure rate, or recovery analytics data.
---

# DORA Integration Skill

## Objective
Generate DORA-compatible deployment and incident recovery data that aligns with Git activity and team scope.

## Read Before You Start
1. `Skills/Playbook/SKILL.md`
2. `Skills/ScriptCreation/SKILL.md`
3. `Skills/Integration/Git/SKILL.md` (for deployment-linked PR consistency)
4. target CSV/metric expectations

## 1) Table Inventory

### Primary fact tables
- `insightly.deployment_frequency`
- `insightly.change_requests`

### Mapping / support tables
- `insightly.team`
- `insightly.teamauthorrelation`
- `insightly.author`
- `insightly.pull_request` (for cross-checking deployment-linked PR behavior)

## 2) Table Relationships (ER-style text)
- `author/team scope` is resolved via `teamauthorrelation` using `authorid`
- `deployment_frequency` rows are grouped by `organization_id`, `team_id`, `authorid`, time
- `change_requests` rows are grouped by `organization_id`, `team_id` or `authorid`, time
- DORA views combine deployment counts and incident/change counts over the same period/team scope

## 3) Metric Dependencies
- `DORA_DEPLOYMENT_FREQUENCY`: count of deployment events in `deployment_frequency`
- `DORA_CFR`: incidents/failures from `change_requests` over deployment denominator
- `DORA_MTTR`: average `change_requests.duration`
- `CICD_DEPLOYMENT_FREQUENCY`: deployment count from `deployment_frequency`

## 4) Dynamic Data Generation Rules
1. **Keep period alignment strict**: deployments and incidents must share the same month/week boundaries.
2. **Keep team alignment strict**: `team_id` and `authorid` must map to valid team-author relations.
3. **CFR realism**:
   - Keep change/failure counts as a plausible small fraction of deployments unless simulating outage periods.
4. **MTTR realism**:
   - Use realistic duration ranges (minutes/hours), avoid random spikes unless intentionally modeled.
5. **Idempotent writes**:
   - Upsert by natural deployment/change identifiers; avoid duplicate deployment_record_id collisions.

## 5) Script Design Pattern
- Section 1: Validation (deployment/change coverage)
- Section 2: Insert/Update (deployment + change records)
- Section 3: Post-check (DORA DF/CFR/MTTR by month/team)

## End Checklist
- deployment and incident windows match period boundaries.
- team_id + authorid mappings are valid.
- CFR denominator (deployments) is non-zero when CFR expected.
- MTTR durations are realistic and documented.

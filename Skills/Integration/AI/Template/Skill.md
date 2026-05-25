---
name: demodashboards-integration-ai-template
description: Template workflow for introducing new AI provider integrations in DemoDashboards. Use when adding or scaffolding provider-specific integration skills beyond existing ones.
---

# AI Integration Skill (Template for Other AI Providers)

## Objective
Provide a reusable, dynamic blueprint for new AI provider integrations (beyond Claude/Copilot).

## 1) Table Inventory (template)
- Provider daily usage table(s)
- Provider event/session table(s)
- Provider-to-source author mapping table/fields
- Team mapping tables (`team`, `teamauthorrelation`)
- Integration ownership (`user_integration_details`)
- Optional summary/aggregation tables

## 2) Relationships (template)
- Provider identity -> source author (`assignedauthorid` or equivalent)
- Source author -> team via `teamauthorrelation`
- Daily/event facts -> org + integration + date
- Optional summary tables must reconcile with daily facts

## 3) Metric Dependency Mapping (template)
For each metric, document:
- source tables
- numerator fields
- denominator fields
- filter flags
- output granularity (author/team/org)

## 4) Dynamic Rules (template)
1. Discover schema at runtime (no hard-coded assumptions where avoidable).
2. Generate facts first, summaries second.
3. Enforce denominator/numerator coherence.
4. Keep JSON payloads valid where charts need dimensions.
5. Use idempotent upsert keys.
6. Add post-check queries that mimic service formulas.

## 5) Required SQL Structure
- Section 1: Validation
- Section 2: Data generation/update
- Section 3: Post-fix metric verification

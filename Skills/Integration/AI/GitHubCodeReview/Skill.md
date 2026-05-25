---
name: demodashboards-integration-ai-github-code-review
description: Handle GitHub code review AI integration patterns for DemoDashboards. Use when tasks involve provider github_code_review analytics or environment-dependent table mappings.
---

# AI Integration Skill (GitHub Code Review)

## Objective
Provide a safe dynamic pattern for provider `github_code_review` integrations where dedicated analytics tables may vary by environment.

## 1) Table Inventory

### Known integration identity table
- `insightly.user_integration_details` (`provider='github_code_review`)

### Candidate dependent tables (environment-specific)
- Any provider-specific review usage table discovered at runtime
- `insightly.pull_request`
- `insightly.pr_reviewer`
- `insightly.author`
- `insightly.teamauthorrelation`
- `insightly.team`

## 2) Relationship Model
- Integration account is discovered from `user_integration_details`.
- Provider usage events (if present) must map to source author/team scope.
- Review-related metrics must reconcile with PR/reviewer records.

## 3) Dynamic Discovery Requirement
Before generation, run schema discovery for provider-specific tables:
- inspect tables/columns matching provider naming patterns
- confirm keys for org, date, author, PR/review reference
- only then generate or update data

## 4) Generation Rules
1. Do not assume fixed table names beyond integration identity.
2. Generate from existing PR/review context; avoid synthetic disconnected rows.
3. Keep writes idempotent by natural keys.
4. Add strict post-check proving rows are joinable to team scope.

## 5) Script Design Pattern
- Section 1: Validation + dynamic table discovery
- Section 2: Data generation/update (provider table + linked context)
- Section 3: Post-check (provider metrics + PR consistency)

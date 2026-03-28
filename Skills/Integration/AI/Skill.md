---
name: demodashboards-integration-ai-index
description: Central AI integration index for DemoDashboards. Use when selecting or routing provider-specific AI data generation workflows across Claude, Copilot, Cursor, and related providers.
---

# AI Integration Index (Dynamic)

## Purpose
Central index for AI integration data-generation skills.

## Provider discovery rule (always run first)
Use `insightly.user_integration_details` to discover active providers dynamically for the target org.

Example discovery query:
```sql
SELECT LOWER(COALESCE(provider,'')) AS provider,
       LOWER(COALESCE(scmprovider,'')) AS scmprovider,
       COUNT(*) AS cnt
FROM insightly.user_integration_details
GROUP BY 1,2
ORDER BY cnt DESC;
```

## Providers found in production snapshot
- `github_copilot / githubcopilot`
- `cursor / cursor`
- `claude_code / claudecode`
- `github_code_review / githubcloud` (integration exists; provider tables may vary)

## Skill mapping
- Copilot: `AI/Copilot/Skill.md`
- Cursor: `AI/Cursor/Skill.md`
- Claude: `AI/Claude/Skill.md`
- GitHub Code Review: `AI/GitHubCodeReview/Skill.md`
- Future providers: start from `AI/Template/Skill.md`

## Dynamic rule
Do not hardcode AI provider scope in scripts.
1. Discover providers for org.
2. Choose matching skill.
3. Generate data with provider-specific tables and shared mapping rules.
4. Include companion tables where org has active usage:
   - Copilot: `github_copilot_user_daily_usage` + `copilot_daily_summary` + `copilot_editor_usage` + `copilot_language_usage` + `copilot_seat_usage`
   - Claude: `claude_code_report` + `claude_code_initial_sync` (and `claude_code_api_key` only if explicitly required)
   - Cursor: `cursor_daily_usage` + `cursor_initial_sync` + `cursor_spending`

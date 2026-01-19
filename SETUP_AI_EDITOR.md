# AI Metrics Editor - Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install the new `openai` package along with existing dependencies.

### 2. Set Environment Variables

Create a `.env` file in the project root:

```bash
# Required for AI features
OPENAI_API_KEY=sk-your-api-key-here

# Database connection (existing)
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# API URL (optional, defaults to localhost:8000)
METRICS_EDITOR_API_URL=http://localhost:8000
```

### 3. Start the API Server

```bash
uvicorn main:app --reload --port 8000
```

The server will now include the new AI endpoints:
- `POST /metrics-editor/ai/plan` - Generate AI plan
- `POST /metrics-editor/ai/apply` - Apply AI plan
- `POST /metrics-editor/ai/preview-impact` - Preview impact

### 4. Start the UI

```bash
streamlit run ui/metric_editor_app.py
```

### 5. Use AI Mode

1. Open the UI in your browser (typically http://localhost:8501)
2. In the sidebar, select **"AI-Driven"** mode
3. Configure your filters (org, date range, scope)
4. Click **"Load eligible scopes"**
5. In the main area, enter your request in natural language
6. Click **"Generate AI Plan"**
7. Review the plan, reasoning, and SQL
8. Click **"Apply AI Plan"** to execute

## Example Requests

### Simple Examples

```
Mark 5 PRs as reviewed in December 2025
```

```
Shift 10 commits from November to December
```

```
Increase unreviewed PRs by 8 for author 123
```

### Intermediate Examples

```
Reduce review time by 20% for team 456 in the last quarter
```

```
Set commit mix to 70% new work, 20% rework, 10% maintenance for November
```

```
Make 3 PRs flashy reviews (quick review, large size) in December
```

### Advanced Examples

```
Adjust metrics to show improved cycle time: reduce review time by 30%, 
reduce deploy time by 15%, and mark 5 additional PRs as reviewed
```

```
Shift 15 commits from October to November, and adjust their work mix 
to 80% new work, 15% rework, 5% maintenance
```

## Architecture Overview

### New Files Created

1. **`metrics_editor/ai_orchestrator.py`**
   - Main AI orchestration logic
   - Manages OpenAI API calls
   - Coordinates validation and plan generation

2. **`metrics_editor/prompt_templates.py`**
   - Specialized prompts for different request types
   - Context-aware prompt building

3. **`metrics_editor/mcp_tools.py`**
   - MCP tool registry for AI
   - Database inspection tools
   - Metric formula and validation tools

4. **`metrics_editor/validators.py`**
   - Multi-layer validation system
   - SQL safety checks
   - Constraint validation
   - In-transaction testing

5. **`AI_METRICS_EDITOR.md`**
   - Comprehensive documentation
   - Architecture details
   - Usage examples

### Modified Files

1. **`metrics_editor/models.py`**
   - Added `AIChangeRequest`
   - Added `AIChangePlan`
   - Added `AIChangeResult`

2. **`metrics_editor/router.py`**
   - Added `/ai/plan` endpoint
   - Added `/ai/apply` endpoint
   - Added `/ai/preview-impact` endpoint

3. **`ui/metric_editor_app.py`**
   - Added mode selector (Traditional vs AI-Driven)
   - Added natural language input field
   - Added AI plan visualization
   - Traditional mode still fully functional

4. **`requirements.txt`**
   - Added `openai>=1.0.0`

## How It Works

### Request Flow

```
User Input (Natural Language)
    ↓
AI Orchestrator
    ↓
Request Classification
    ↓
Context Building (metrics, data, constraints)
    ↓
OpenAI API with Function Calling
    ↓
AI inspects database via MCP tools
    ↓
AI generates SQL plan
    ↓
Validation Layer
    ├─ SQL Safety Check
    ├─ Constraint Validation
    └─ In-Transaction Test
    ↓
Plan returned to user
    ↓
User reviews and approves
    ↓
Changes applied
```

### AI Function Calling

The AI has access to these tools:

1. **`inspect_pr_data`** - Query pull request records
2. **`inspect_commit_data`** - Query commit records
3. **`validate_metric_impact`** - Check metric dependencies
4. **`get_metric_formula`** - Understand metric calculations

The AI uses these tools to:
- Understand current database state
- Identify which records to modify
- Validate feasibility
- Generate safe SQL

### Validation Layers

1. **SQL Safety**
   - No DELETE, DROP, TRUNCATE, ALTER
   - All UPDATEs require WHERE clauses
   - Parameterized queries only

2. **Constraint Validation**
   - Reviewed + Unreviewed = Total Merged
   - Flashy reviews ≤ Reviewed PRs
   - Hotfix PRs ≤ Release PRs
   - Cycle time = Coding + Review + Deploy time
   - Work mix percentages sum to 100%

3. **In-Transaction Testing**
   - Execute changes in nested transaction
   - Validate all constraints
   - Rollback automatically
   - No side effects

## Cost Considerations

### OpenAI API Costs

- **Model**: GPT-4o (default)
- **Average request**: 2,000-5,000 tokens
- **Estimated cost**: $0.01-0.05 per request
- **Function calls**: 2-5 per request

### Optimization Tips

1. **Be specific in requests**
   - Clear requests reduce back-and-forth
   - Fewer function calls needed

2. **Use Traditional mode for routine tasks**
   - AI mode for exploratory/custom requests
   - Traditional mode for repeatable operations

3. **Batch similar requests**
   - Combine related changes
   - Reduce total API calls

## Troubleshooting

### "OpenAI API key not found"

```bash
# Set in .env file
OPENAI_API_KEY=sk-your-key-here

# Or export in shell
export OPENAI_API_KEY=sk-your-key-here
```

### "Failed to generate AI plan"

Check:
1. API key is valid
2. OpenAI account has credits
3. Network connectivity
4. Request is clear and specific

### "Plan validation failed"

The request violates constraints. Try:
1. Rephrasing the request
2. Breaking into smaller requests
3. Checking current data state
4. Reviewing affected metrics

### "Transaction validation failed"

Constraint violation detected after simulation. Check:
1. Metric dependencies
2. Data consistency
3. Constraint relationships

## Migration Strategy

### Phase 1: Parallel Operation (Current)
- Both Traditional and AI modes available
- Users can choose based on task
- Traditional mode unchanged

### Phase 2: Gradual Adoption
- Encourage AI mode for custom requests
- Keep Traditional for automation
- Gather feedback

### Phase 3: Full Integration
- AI mode becomes primary
- Traditional mode for specific use cases
- Automated workflows use API directly

## Testing

### Unit Tests (TODO)

```python
# Test AI orchestrator
def test_classify_request():
    orchestrator = AIOrchestrator(session)
    request_type = orchestrator._classify_request(
        "Increase unreviewed PRs by 10"
    )
    assert request_type == "pr_review"

# Test validators
def test_flashy_constraint():
    validator = MetricValidator(session)
    is_valid, errors = validator._validate_flashy_constraints(scope)
    assert is_valid
```

### Integration Tests (TODO)

```python
# Test end-to-end flow
def test_ai_plan_generation():
    request = AIChangeRequest(
        user_intent="Mark 5 PRs as reviewed",
        scope=scope,
    )
    plan = orchestrator.process_change_request(request)
    assert len(plan.sql_statements) > 0
    assert plan.estimated_rows > 0
```

### Manual Testing Checklist

- [ ] Generate plan for simple request
- [ ] Verify SQL statements are safe
- [ ] Check validation passes
- [ ] Apply plan and verify changes
- [ ] Test constraint violations are caught
- [ ] Test complex multi-metric requests
- [ ] Verify Traditional mode still works

## Security Considerations

1. **SQL Injection Prevention**
   - All queries parameterized
   - No string concatenation
   - Validation layer enforces

2. **Access Control**
   - Same as Traditional mode
   - Respects scope filters
   - No privilege escalation

3. **Audit Trail**
   - All plans logged
   - User intent preserved
   - SQL statements saved

4. **API Key Security**
   - Store in .env (not in code)
   - Never commit to git
   - Rotate regularly

## Performance

### Typical Response Times

- **Plan generation**: 3-8 seconds
- **Validation**: < 1 second
- **Application**: < 1 second

### Optimization

- Validation runs in parallel where possible
- Database queries optimized
- Transaction rollback is fast

## Next Steps

1. **Test the system**
   - Try various requests
   - Verify constraints
   - Check edge cases

2. **Gather feedback**
   - User experience
   - Accuracy of plans
   - Performance issues

3. **Iterate**
   - Improve prompts
   - Add more validation
   - Enhance error messages

4. **Extend**
   - Add more MCP tools
   - Support more metrics
   - Improve AI reasoning

## Support

For questions or issues:
1. Check `AI_METRICS_EDITOR.md` for details
2. Review logs in `logs/metric_editor/`
3. Test in Traditional mode first
4. Contact development team

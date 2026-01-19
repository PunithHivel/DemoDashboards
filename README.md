# DemoDashboards

A comprehensive dashboard system with an AI-driven metrics editor.

## Features

- **Traditional Metrics Editor**: Rule-based metric changes with predefined actions
- **AI-Driven Metrics Editor**: Natural language requests powered by OpenAI GPT-4
- **Multi-layer Validation**: Ensures data integrity and constraint preservation
- **Dual Mode Operation**: Choose the right tool for each task

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```bash
# Required for AI features
OPENAI_API_KEY=sk-your-api-key-here

# Database connection
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Optional: API URL
METRICS_EDITOR_API_URL=http://localhost:8000
```

### 3. Run the API

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000/`.

### 4. Run the Metrics Editor UI

In a separate terminal:

```bash
streamlit run ui/metric_editor_app.py
```

The UI will open in your browser (typically `http://localhost:8501`).

## AI-Driven Metrics Editor

### Overview

The AI-driven metrics editor allows you to describe metric changes in natural language. The AI analyzes your request, inspects the database, and generates safe SQL transformations while preserving all metric dependencies.

### Example Requests

```
Mark 5 PRs as reviewed in December 2025
Shift 10 commits from November to December
Reduce review time by 20% for team 456
Set commit mix to 70% new work, 20% rework, 10% maintenance
```

### How to Use

1. Open the UI and select **"AI-Driven"** mode in the sidebar
2. Configure your filters (organization, date range, scope)
3. Click **"Load eligible scopes"**
4. Enter your request in natural language
5. Click **"Generate AI Plan"**
6. Review the plan, reasoning, and SQL statements
7. Click **"Apply AI Plan"** to execute

### Documentation

- **[AI_METRICS_EDITOR.md](AI_METRICS_EDITOR.md)** - Complete architecture and design
- **[SETUP_AI_EDITOR.md](SETUP_AI_EDITOR.md)** - Detailed setup guide
- **[AI_EDITOR_QUICK_REFERENCE.md](AI_EDITOR_QUICK_REFERENCE.md)** - Quick reference
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Implementation overview

## Traditional Metrics Editor

The traditional editor provides predefined actions for specific metrics:

- Shift PRs/commits between months
- Mark PRs as reviewed/unreviewed
- Adjust PR sizes and durations
- Toggle PR flags (release, hotfix)
- Modify commit work mix

Select **"Traditional"** mode in the UI to use this approach.

## Architecture

### Core Components

- **AI Orchestrator** - Manages AI workflow and OpenAI integration
- **Prompt Templates** - Specialized prompts for different request types
- **MCP Tool Registry** - Database inspection tools for AI
- **Validators** - Multi-layer validation and constraint checking
- **Traditional Engine** - Rule-based metric change engine
- **API Router** - FastAPI endpoints for both modes
- **Streamlit UI** - Interactive web interface

### Safety Features

✓ SQL injection prevention (parameterized queries)  
✓ No DELETE/DROP/TRUNCATE operations  
✓ All UPDATEs require WHERE clauses  
✓ In-transaction validation with rollback  
✓ Multi-layer constraint checking  
✓ Audit trail (all plans logged)  

### Constraints Enforced

- Reviewed + Unreviewed = Total Merged PRs
- Flashy reviews ≤ Reviewed PRs
- Hotfix PRs ≤ Release PRs
- Cycle time = Coding + Review + Deploy time
- Work mix percentages sum to 100%
- All durations ≥ 0

## API Endpoints

### Traditional Endpoints

- `GET /metrics-editor/catalog` - Get metric catalog
- `POST /metrics-editor/current` - Get current metric values
- `POST /metrics-editor/impact` - Preview change impact
- `POST /metrics-editor/apply` - Apply changes
- `POST /metrics-editor/eligible` - Get eligible entities
- `GET /metrics-editor/history` - View change history

### AI Endpoints

- `POST /metrics-editor/ai/plan` - Generate AI plan from natural language
- `POST /metrics-editor/ai/apply` - Apply AI-generated plan
- `POST /metrics-editor/ai/preview-impact` - Preview AI plan impact

## Examples

See `examples/ai_editor_example.py` for programmatic usage examples.

## Cost Considerations

The AI-driven editor uses OpenAI's API:
- **Per request**: $0.01-0.05
- **Typical session**: $0.10-0.50 (5-10 requests)
- **Monthly (moderate use)**: $5-20

Use Traditional mode for routine tasks to minimize costs.

## Troubleshooting

### "OpenAI API key not found"
Set `OPENAI_API_KEY` in your `.env` file.

### "Plan validation failed"
Your request may violate constraints. Try rephrasing or breaking into smaller requests.

### "Transaction validation failed"
Constraint violation detected. Review affected metrics and dependencies.

See [SETUP_AI_EDITOR.md](SETUP_AI_EDITOR.md) for more troubleshooting tips.

## Development

### Project Structure

```
DemoDashboards/
├── metrics_editor/          # Metrics editor backend
│   ├── ai_orchestrator.py   # AI orchestration
│   ├── prompt_templates.py  # AI prompts
│   ├── mcp_tools.py         # Database tools for AI
│   ├── validators.py        # Validation layer
│   ├── engine.py            # Traditional engine
│   ├── router.py            # API endpoints
│   └── models.py            # Pydantic models
├── ui/                      # Streamlit UI
│   └── metric_editor_app.py
├── examples/                # Usage examples
│   └── ai_editor_example.py
├── logs/                    # Change history logs
│   └── metric_editor/
└── config/                  # Configuration
    └── metric_catalog.json
```

### Running Tests

```bash
# TODO: Add test suite
pytest tests/
```

## Support

For questions or issues:
1. Check the documentation files
2. Review logs in `logs/metric_editor/`
3. Test in Traditional mode first
4. Contact the development team

## License

[Add your license here]

## Contributors

[Add contributors here]

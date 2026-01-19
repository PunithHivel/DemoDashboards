"""
Example script demonstrating the AI-driven metrics editor.

This script shows how to use the AI orchestrator programmatically.
"""

from datetime import date

from sqlalchemy.orm import Session

from db.session import get_db_session
from metrics_editor.ai_orchestrator import AIOrchestrator
from metrics_editor.models import AIChangeRequest, MetricScope


def example_simple_review_change():
    """Example: Mark PRs as reviewed."""
    print("=" * 60)
    print("Example 1: Simple Review Change")
    print("=" * 60)
    
    # Get database session
    session: Session = next(get_db_session())
    
    # Create orchestrator
    orchestrator = AIOrchestrator(session)
    
    # Define scope
    scope = MetricScope(
        organization_id=2159,
        repo_id=None,
        team_id=None,
        author_ids=None,
        start_date=date(2025, 12, 1),
        end_date=date(2026, 1, 1),
    )
    
    # Create request
    request = AIChangeRequest(
        user_intent="Mark 5 PRs as reviewed in December 2025",
        scope=scope,
    )
    
    # Generate plan
    print("\nGenerating AI plan...")
    try:
        plan = orchestrator.process_change_request(request)
        
        print(f"\nPlan ID: {plan.plan_id}")
        print(f"Request Type: {plan.request_type}")
        print(f"Estimated Rows: {plan.estimated_rows}")
        print(f"\nReasoning:\n{plan.reasoning}")
        print(f"\nAffected Metrics: {', '.join(plan.affected_metrics)}")
        print(f"\nValidation Checks:")
        for check in plan.validation_checks:
            print(f"  ✓ {check}")
        
        if plan.warnings:
            print(f"\nWarnings:")
            for warning in plan.warnings:
                print(f"  ⚠ {warning}")
        
        print(f"\nSQL Statements:")
        for i, (stmt, params) in enumerate(zip(plan.sql_statements, plan.sql_params), 1):
            print(f"\n  Statement {i}:")
            print(f"    {stmt[:100]}...")
            print(f"    Params: {list(params.keys())}")
        
        print("\n✓ Plan generated successfully!")
        
    except Exception as e:
        print(f"\n✗ Failed to generate plan: {e}")
    
    finally:
        session.close()


def example_commit_shift():
    """Example: Shift commits between months."""
    print("\n" + "=" * 60)
    print("Example 2: Commit Date Shift")
    print("=" * 60)
    
    session: Session = next(get_db_session())
    orchestrator = AIOrchestrator(session)
    
    scope = MetricScope(
        organization_id=2159,
        repo_id=None,
        team_id=None,
        author_ids=[123],  # Specific author
        start_date=date(2025, 10, 1),
        end_date=date(2026, 1, 1),
    )
    
    request = AIChangeRequest(
        user_intent="Shift 10 commits from November to December for author 123",
        scope=scope,
    )
    
    print("\nGenerating AI plan...")
    try:
        plan = orchestrator.process_change_request(request)
        
        print(f"\nPlan ID: {plan.plan_id}")
        print(f"Request Type: {plan.request_type}")
        print(f"Estimated Rows: {plan.estimated_rows}")
        print(f"\nReasoning:\n{plan.reasoning}")
        
        print("\n✓ Plan generated successfully!")
        
    except Exception as e:
        print(f"\n✗ Failed to generate plan: {e}")
    
    finally:
        session.close()


def example_complex_change():
    """Example: Complex multi-metric change."""
    print("\n" + "=" * 60)
    print("Example 3: Complex Multi-Metric Change")
    print("=" * 60)
    
    session: Session = next(get_db_session())
    orchestrator = AIOrchestrator(session)
    
    scope = MetricScope(
        organization_id=2159,
        repo_id=None,
        team_id=456,  # Specific team
        author_ids=None,
        start_date=date(2025, 12, 1),
        end_date=date(2026, 1, 1),
    )
    
    request = AIChangeRequest(
        user_intent=(
            "Improve metrics for team 456 in December: "
            "reduce review time by 25%, increase reviewed PRs by 5, "
            "and add 2 flashy reviews"
        ),
        scope=scope,
    )
    
    print("\nGenerating AI plan...")
    try:
        plan = orchestrator.process_change_request(request)
        
        print(f"\nPlan ID: {plan.plan_id}")
        print(f"Request Type: {plan.request_type}")
        print(f"Estimated Rows: {plan.estimated_rows}")
        print(f"\nReasoning:\n{plan.reasoning}")
        print(f"\nAffected Metrics: {', '.join(plan.affected_metrics)}")
        
        print("\n✓ Plan generated successfully!")
        
    except Exception as e:
        print(f"\n✗ Failed to generate plan: {e}")
    
    finally:
        session.close()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("AI-Driven Metrics Editor - Examples")
    print("=" * 60)
    print("\nNote: These examples require:")
    print("  1. OPENAI_API_KEY environment variable set")
    print("  2. Database connection configured")
    print("  3. Valid organization/team/author IDs")
    print("\n")
    
    # Run examples
    example_simple_review_change()
    example_commit_shift()
    example_complex_change()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)

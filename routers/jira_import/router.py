from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
import csv
import io
from sqlalchemy.orm import Session
from schemas.jira_import import (
    BoardImport,
    JiraSubBoardImport,
    SprintImport,
    IssueImport,
    SprintIssueMappingImport,
    TeamBoardMappingImport,
    IssueEventLogImport,
    JiraGitMappingImport
)
from repositories.jira_import_repository import JiraImportRepository
from db.session import get_db_session

router = APIRouter(prefix="/jira-import", tags=["JIRA Import"])
_repository = JiraImportRepository()


def parse_csv_to_dict(file_content: str) -> List[dict]:
    """Parse CSV content to list of dictionaries"""
    csv_reader = csv.DictReader(io.StringIO(file_content))
    return [row for row in csv_reader]


def clean_empty_values(data: dict) -> dict:
    """Convert empty strings to None for proper database handling"""
    return {k: (None if v == '' else v) for k, v in data.items()}


@router.post("/board")
async def import_boards(
    file: UploadFile = File(...),
    org_id: int = Form(...),
    user_integration_id: Optional[int] = Form(None),
    session: Session = Depends(get_db_session)
):
    """
    Import boards from CSV file
    
    **Auto-generated fields (DO NOT include in CSV):**
    - id (IDENTITY column)
    - created_at (CURRENT_TIMESTAMP)
    
    **Required parameters:**
    - org_id: Organization ID
    - user_integration_id: Optional user integration ID
    
    **CSV Columns:**
    - account_id, active, avatar_uri, display_name, entity_id
    - is_private, jira_board_id, board_key, name, self
    - uuid, is_deleted, auto_generated_sprint, azure_project_id
    - azure_project_name, azure_org_name, last_issue_update_time
    - has_permission, valid, board_type
    """
    try:
        content = await file.read()
        csv_data = parse_csv_to_dict(content.decode('utf-8'))
        
        # Clean and validate data
        boards = []
        for row in csv_data:
            cleaned_row = clean_empty_values(row)
            # Remove 'id' and 'created_at' if present in CSV
            cleaned_row.pop('id', None)
            cleaned_row.pop('created_at', None)
            boards.append(cleaned_row)
        
        # Import to database
        result = _repository.import_boards(session, boards, org_id, user_integration_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Boards imported successfully",
                "org_id": org_id,
                "user_integration_id": user_integration_id,
                **result
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jira-sub-board")
async def import_jira_sub_boards(
    file: UploadFile = File(...),
    org_id: int = Form(...),
    user_integration_id: Optional[int] = Form(None),
    session: Session = Depends(get_db_session)
):
    """
    Import jira sub boards from CSV file
    
    **Auto-generated fields (DO NOT include in CSV):**
    - id (IDENTITY column)
    
    **Required parameters:**
    - org_id: Organization ID
    - user_integration_id: Optional user integration ID
    
    **CSV Columns:**
    - sub_board_id (required), self, name, type, jira_board_id
    - created_at, is_deleted, board_id, jira_jql_id
    - jira_jql_url, jql, jql_updated
    """
    try:
        content = await file.read()
        csv_data = parse_csv_to_dict(content.decode('utf-8'))
        
        # Clean and validate data
        sub_boards = []
        for row in csv_data:
            cleaned_row = clean_empty_values(row)
            # Remove 'id' if present in CSV
            cleaned_row.pop('id', None)
            cleaned_row.pop('organizationid', None)  # Will be set from org_id
            sub_boards.append(cleaned_row)
        
        # Import to database
        result = _repository.import_jira_sub_boards(session, sub_boards, org_id, user_integration_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Jira sub boards imported successfully",
                "org_id": org_id,
                "user_integration_id": user_integration_id,
                **result
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sprint")
async def import_sprints(
    file: UploadFile = File(...),
    org_id: int = Form(...),
    user_integration_id: Optional[int] = Form(None),
    session: Session = Depends(get_db_session)
):
    """
    Import sprints from CSV file
    
    **Auto-generated fields (DO NOT include in CSV):**
    - id (nextval sequence)
    - created_at (CURRENT_TIMESTAMP)
    
    **Required parameters:**
    - org_id: Organization ID
    - user_integration_id: Optional user integration ID
    
    **CSV Columns:**
    - is_deleted, board_id, complete_date, end_date, goal
    - name, sprint_jira_id, start_date, state, self_url
    - jira_board_id, auto_generated, azure_org_name, metrics_generated
    - sub_board_id, type, shared_boards, sprint_path, valid
    """
    try:
        content = await file.read()
        csv_data = parse_csv_to_dict(content.decode('utf-8'))
        
        # Clean and validate data
        sprints = []
        for row in csv_data:
            cleaned_row = clean_empty_values(row)
            # Remove 'id', 'created_at', 'org_id' if present in CSV
            cleaned_row.pop('id', None)
            cleaned_row.pop('created_at', None)
            cleaned_row.pop('org_id', None)  # Will be set from parameter
            sprints.append(cleaned_row)
        
        # Import to database
        result = _repository.import_sprints(session, sprints, org_id, user_integration_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Sprints imported successfully",
                "org_id": org_id,
                "user_integration_id": user_integration_id,
                **result
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/issue")
async def import_issues(
    file: UploadFile = File(...),
    org_id: int = Form(...),
    user_integration_id: Optional[int] = Form(None),
    session: Session = Depends(get_db_session)
):
    """
    Import issues from CSV file
    
    **Auto-generated fields (DO NOT include in CSV):**
    - id (nextval sequence)
    - created_at (CURRENT_TIMESTAMP)
    
    **Required parameters:**
    - org_id: Organization ID
    - user_integration_id: Optional user integration ID
    
    **CSV Columns:**
    - board_id, issue_type, priority, resolution_date, time_spent
    - work_ratio, parent_id, is_deleted, assignee_id, creator_id
    - current_progress, due_date, issue_id, key, parent_issue_id
    - project_id, reporter_id, status, status_change_date, summary
    - time_original_estimate, time_aggregate_estimate, total_progress
    - story_point, description, sprint_id, jira_create_date, jira_updated_date
    - issue_url, jira_cycle_time, api_url, parent_task_id, assignees
    - release_id, milestone_id, issue_level, original_assignee, original_creator
    - original_reporter, old_assignee, old_creator, old_reporter, is_epic
    - product, allocation, t_shirt_size, estimated_storypoints, sub_boards
    - azure_org_id, value_milestone_id, initiative_id, hierarchy_level
    - epic_id, feature_id, investment_id, hierarchal_issue_type
    - created_by_hierarchy, mapping_corrected, custom_fields, sprint_path
    """
    try:
        content = await file.read()
        csv_data = parse_csv_to_dict(content.decode('utf-8'))
        
        # Clean and validate data
        issues = []
        for row in csv_data:
            cleaned_row = clean_empty_values(row)
            # Remove 'id', 'created_at', 'org_id' if present in CSV
            cleaned_row.pop('id', None)
            cleaned_row.pop('created_at', None)
            cleaned_row.pop('org_id', None)  # Will be set from parameter
            issues.append(cleaned_row)
        
        # Import to database
        result = _repository.import_issues(session, issues, org_id, user_integration_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Issues imported successfully",
                "org_id": org_id,
                "user_integration_id": user_integration_id,
                **result
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sprint-issue-mapping")
async def import_sprint_issue_mappings(
    file: UploadFile = File(...),
    org_id: int = Form(...),
    user_integration_id: Optional[int] = Form(None),
    session: Session = Depends(get_db_session)
):
    """
    Import sprint issue mappings from CSV file
    
    **Auto-generated fields (DO NOT include in CSV):**
    - id (IDENTITY column)
    - created_at (CURRENT_TIMESTAMP)
    
    **Required parameters:**
    - org_id: Organization ID
    - user_integration_id: Optional user integration ID
    
    **CSV Columns:**
    - issue_id (required), sprint_id (required)
    - is_deleted, resolution
    """
    try:
        content = await file.read()
        csv_data = parse_csv_to_dict(content.decode('utf-8'))
        
        # Clean and validate data
        mappings = []
        for row in csv_data:
            cleaned_row = clean_empty_values(row)
            # Remove 'id', 'created_at', 'org_id' if present in CSV
            cleaned_row.pop('id', None)
            cleaned_row.pop('created_at', None)
            cleaned_row.pop('org_id', None)  # Will be set from parameter
            mappings.append(cleaned_row)
        
        # Import to database
        result = _repository.import_sprint_issue_mappings(session, mappings, org_id, user_integration_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Sprint issue mappings imported successfully",
                "org_id": org_id,
                "user_integration_id": user_integration_id,
                **result
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/team-board-mapping")
async def import_team_board_mappings(
    file: UploadFile = File(...),
    org_id: int = Form(...),
    user_integration_id: Optional[int] = Form(None),
    session: Session = Depends(get_db_session)
):
    """
    Import team board mappings from CSV file
    
    **Auto-generated fields (DO NOT include in CSV):**
    - id (nextval sequence)
    
    **Required parameters:**
    - org_id: Organization ID (will override organization_id in CSV)
    - user_integration_id: Optional user integration ID
    
    **CSV Columns:**
    - team_name, team_id, board_name, board_id
    - client_team_name, assignment_group, mapping_processed
    """
    try:
        content = await file.read()
        csv_data = parse_csv_to_dict(content.decode('utf-8'))
        
        # Clean and validate data
        mappings = []
        for row in csv_data:
            cleaned_row = clean_empty_values(row)
            # Remove 'id', 'organization_id' if present in CSV
            cleaned_row.pop('id', None)
            cleaned_row.pop('organization_id', None)  # Will be set from org_id parameter
            mappings.append(cleaned_row)
        
        # Import to database
        result = _repository.import_team_board_mappings(session, mappings, org_id, user_integration_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Team board mappings imported successfully",
                "org_id": org_id,
                "user_integration_id": user_integration_id,
                **result
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/issue-event-log")
async def import_issue_event_logs(
    file: UploadFile = File(...),
    org_id: int = Form(...),
    user_integration_id: int = Form(...),
    session: Session = Depends(get_db_session)
):
    """
    Import issue event logs from CSV file for sprint metrics tracking.
    Uses high-performance PostgreSQL COPY command for bulk inserts.
    
    This table tracks planned/unplanned work and completed/spillover items per sprint.
    Used for calculating sprint velocity, predictability, and commitment metrics.
    
    **Auto-generated fields (DO NOT include in CSV):**
    - id (sequence)
    
    **Required parameters:**
    - org_id: Organization ID
    - user_integration_id: User integration ID (required for this table)
    
    **CSV Columns:**
    - issue_id, sprint_id, assignee_id, board_id, issue_key
    - status (e.g., 'Completed', 'Done', 'Closed', 'In Progress')
    - resolution_date, issue_added_timestamp
    - sprint_started_timestamp, sprint_closed_timestamp
    - planned (true/false - was item planned at sprint start?)
    - spillover (true/false - did item spill over to next sprint?)
    - deleted, story_point
    - parent_issue_id, original_assignee, old_assignee
    - change_date, change_timestamp
    
    **Metric Calculation:**
    - Planned Completed: planned=true, spillover=false, status in completed statuses
    - Unplanned Completed: planned=false, spillover=false, status in completed statuses
    - Planned Spillover: planned=true, spillover=true
    - Unplanned Spillover: planned=false, spillover=true
    """
    try:
        content = await file.read()
        csv_data = parse_csv_to_dict(content.decode('utf-8'))
        
        # Clean and validate data
        events = []
        for row in csv_data:
            cleaned_row = clean_empty_values(row)
            # Remove 'id', 'created_date', 'modifieddate', 'org_id', 'user_integration_id' if present
            cleaned_row.pop('id', None)
            cleaned_row.pop('created_date', None)
            cleaned_row.pop('modifieddate', None)
            cleaned_row.pop('org_id', None)
            cleaned_row.pop('user_integration_id', None)
            
            # Convert boolean strings to actual booleans
            if 'planned' in cleaned_row and cleaned_row['planned'] is not None:
                cleaned_row['planned'] = str(cleaned_row['planned']).lower() == 'true'
            if 'spillover' in cleaned_row and cleaned_row['spillover'] is not None:
                cleaned_row['spillover'] = str(cleaned_row['spillover']).lower() == 'true'
            if 'deleted' in cleaned_row and cleaned_row['deleted'] is not None:
                cleaned_row['deleted'] = str(cleaned_row['deleted']).lower() == 'true'
            
            events.append(cleaned_row)
        
        # Import to database using bulk COPY
        result = _repository.import_issue_event_logs(session, events, org_id, user_integration_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Issue event logs imported successfully (bulk COPY)",
                "org_id": org_id,
                "user_integration_id": user_integration_id,
                **result
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jira-git-mapping")
async def import_jira_git_mappings(
    file: UploadFile = File(...),
    org_id: int = Form(...),
    limit: Optional[int] = Form(None),
    session: Session = Depends(get_db_session)
):
    """
    Import JIRA-Git activity mappings from CSV file.
    Uses high-performance PostgreSQL COPY command for bulk inserts.
    
    This table links Jira issues with Git activities (commits and pull requests),
    enabling metrics like cycle time, developer productivity, and issue-to-code traceability.
    
    **Table**: `insightly.jira_issue_git_activity_mapping`
    
    **Auto-generated/Auto-fetched fields (DO NOT include in CSV):**
    - id (sequence - auto-generated)
    - activity_date (auto-fetched from commit.date or pull_request.created_on)
    - actor (auto-fetched from commit.author_id or pull_request.author_id)
    
    **Required parameters:**
    - org_id: Organization ID (will override organization_id in CSV)
    
    **Optional parameters:**
    - limit: Maximum number of records to import from CSV (default: all records)
    
    **CSV Columns (Required):**
    - issue_id: Internal database ID of the Jira issue (insightly_jira.issue.id)
    - jira_issue_id: External Jira issue ID from Jira API (e.g., "88")
    - issue_key: Human-readable Jira issue key (e.g., "VEC-88")
    - activity_type: Type of Git activity - "COMMIT", "PULLREQUEST", or "MERGE_COMMIT"
    - activity_id: Foreign key to commit.id or pull_request.id
    
    **CSV Columns (Optional):**
    - azure_issue_url: Azure DevOps issue URL (for Azure integrations)
    - jira_hotfix_pr: Hotfix PR indicator
    
    **Activity Types:**
    - COMMIT: Links to insightly.commit table (fetches commit.date and commit.author_id)
    - PULLREQUEST: Links to insightly.pull_request table (fetches pull_request.created_on and pull_request.author_id)
    - MERGE_COMMIT: Links to insightly.commit table (fetches commit.date and commit.author_id)
    
    **Important Notes:**
    - The endpoint automatically fetches activity_date and actor from the respective tables
    - If activity_id is not found in the corresponding table, that mapping will be skipped
    - The response includes both inserted_count and skipped_count
    
    **Usage:**
    - Jira cycle time calculation (first commit to PR merge)
    - Developer productivity per issue
    - Issue-to-code traceability
    - Sprint velocity with Git activity correlation
    """
    try:
        content = await file.read()
        csv_data = parse_csv_to_dict(content.decode('utf-8'))
        
        # Clean and validate data
        mappings = []
        for row in csv_data:
            cleaned_row = clean_empty_values(row)
            # Remove fields that should not be in CSV or will be overridden
            cleaned_row.pop('id', None)
            cleaned_row.pop('organization_id', None)  # Will be set from org_id parameter
            cleaned_row.pop('activity_date', None)  # Will be fetched from activity table
            cleaned_row.pop('actor', None)  # Will be fetched from activity table
            mappings.append(cleaned_row)
        
        # Apply limit if specified
        if limit and limit > 0:
            mappings = mappings[:limit]
        
        # Import to database using bulk COPY
        result = _repository.import_jira_git_mappings(session, mappings, org_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "JIRA-Git mappings imported successfully (bulk COPY)",
                "org_id": org_id,
                "limit_applied": limit if limit else "no limit",
                **result
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

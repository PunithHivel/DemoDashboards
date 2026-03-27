from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# Board Schema
class BoardImport(BaseModel):
    account_id: Optional[str] = None
    active: Optional[str] = None
    avatar_uri: Optional[str] = None
    display_name: Optional[str] = None
    entity_id: Optional[str] = None
    is_private: Optional[bool] = None
    jira_board_id: Optional[str] = None
    board_key: Optional[str] = None
    name: Optional[str] = None
    self: Optional[str] = None
    uuid: Optional[str] = None
    is_deleted: Optional[bool] = False
    auto_generated_sprint: Optional[bool] = False
    azure_project_id: Optional[str] = None
    azure_project_name: Optional[str] = None
    azure_org_name: Optional[str] = None
    last_issue_update_time: Optional[datetime] = None
    has_permission: Optional[bool] = None
    valid: Optional[bool] = None
    board_type: Optional[str] = None


# Jira Sub Board Schema
class JiraSubBoardImport(BaseModel):
    sub_board_id: str
    self: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    jira_board_id: Optional[str] = None
    is_deleted: Optional[bool] = None
    board_id: Optional[int] = None
    jira_jql_id: Optional[str] = None
    jira_jql_url: Optional[str] = None
    jql: Optional[str] = None
    jql_updated: Optional[bool] = None


# Sprint Schema
class SprintImport(BaseModel):
    is_deleted: Optional[bool] = None
    board_id: Optional[int] = None
    complete_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    goal: Optional[str] = None
    name: Optional[str] = None
    sprint_jira_id: Optional[str] = None
    start_date: Optional[datetime] = None
    state: Optional[str] = None
    self_url: Optional[str] = None
    jira_board_id: Optional[str] = None
    auto_generated: Optional[bool] = False
    azure_org_name: Optional[str] = None
    metrics_generated: Optional[bool] = False
    sub_board_id: Optional[int] = None
    type: Optional[str] = None
    shared_boards: Optional[str] = None
    sprint_path: Optional[str] = None
    valid: Optional[bool] = None


# Issue Schema
class IssueImport(BaseModel):
    board_id: Optional[int] = None
    issue_type: Optional[str] = None
    priority: Optional[str] = None
    resolution_date: Optional[datetime] = None
    time_spent: Optional[int] = None
    work_ratio: Optional[str] = None
    parent_id: Optional[int] = None
    is_deleted: Optional[bool] = False
    assignee_id: Optional[int] = None
    creator_id: Optional[int] = None
    current_progress: Optional[int] = None
    due_date: Optional[datetime] = None
    issue_id: Optional[str] = None
    key: Optional[str] = None
    parent_issue_id: Optional[str] = None
    project_id: Optional[int] = None
    reporter_id: Optional[int] = None
    status: Optional[str] = None
    status_change_date: Optional[datetime] = None
    summary: Optional[str] = None
    time_original_estimate: Optional[str] = None
    time_aggregate_estimate: Optional[str] = None
    total_progress: Optional[int] = None
    story_point: Optional[float] = None
    description: Optional[str] = None
    sprint_id: Optional[int] = None
    jira_create_date: Optional[datetime] = None
    jira_updated_date: Optional[datetime] = None
    issue_url: Optional[str] = None
    jira_cycle_time: Optional[int] = None
    api_url: Optional[str] = None
    parent_task_id: Optional[int] = None
    assignees: Optional[list] = None
    release_id: Optional[int] = None
    milestone_id: Optional[int] = None
    issue_level: Optional[str] = None
    original_assignee: Optional[int] = None
    original_creator: Optional[int] = None
    original_reporter: Optional[int] = None
    old_assignee: Optional[int] = None
    old_creator: Optional[int] = None
    old_reporter: Optional[int] = None
    is_epic: Optional[bool] = False
    product: Optional[str] = "Unassigned"
    allocation: Optional[str] = "Unallocated"
    t_shirt_size: Optional[str] = None
    estimated_storypoints: Optional[int] = None
    sub_boards: Optional[str] = None
    azure_org_id: Optional[str] = None
    value_milestone_id: Optional[int] = None
    initiative_id: Optional[int] = None
    hierarchy_level: Optional[str] = None
    epic_id: Optional[int] = None
    feature_id: Optional[int] = None
    investment_id: Optional[int] = None
    hierarchal_issue_type: Optional[str] = None
    created_by_hierarchy: bool = False
    mapping_corrected: Optional[bool] = False
    custom_fields: Optional[dict] = None
    sprint_path: Optional[str] = None


# Sprint Issue Mapping Schema
class SprintIssueMappingImport(BaseModel):
    issue_id: int
    sprint_id: int
    is_deleted: Optional[bool] = None
    resolution: Optional[str] = None


# Team Board Mapping Schema
class TeamBoardMappingImport(BaseModel):
    team_name: Optional[str] = None
    team_id: Optional[int] = None
    board_name: Optional[str] = None
    board_id: Optional[int] = None
    client_team_name: Optional[str] = None
    assignment_group: Optional[str] = None
    mapping_processed: Optional[bool] = True


# Issue Event Log Schema (for sprint metrics: planned/unplanned, completed/spillover)
class IssueEventLogImport(BaseModel):
    issue_id: Optional[int] = None
    sprint_id: Optional[int] = None
    assignee_id: Optional[int] = None
    board_id: Optional[int] = None
    issue_key: Optional[str] = None
    status: Optional[str] = None
    resolution_date: Optional[datetime] = None
    issue_added_timestamp: Optional[datetime] = None
    sprint_started_timestamp: Optional[datetime] = None
    sprint_closed_timestamp: Optional[datetime] = None
    planned: Optional[bool] = None
    spillover: Optional[bool] = None
    deleted: Optional[bool] = False
    parent_issue_id: Optional[str] = None
    story_point: Optional[float] = None
    original_assignee: Optional[int] = None
    old_assignee: Optional[int] = None
    change_date: Optional[datetime] = None
    change_timestamp: Optional[datetime] = None


# JIRA-Git Activity Mapping Schema
class JiraGitMappingImport(BaseModel):
    issue_id: Optional[int] = None
    jira_issue_id: Optional[str] = None
    issue_key: Optional[str] = None
    activity_type: Optional[str] = None  # "COMMIT", "PULLREQUEST", or "MERGE_COMMIT"
    activity_id: Optional[int] = None
    azure_issue_url: Optional[str] = None
    jira_hotfix_pr: Optional[str] = None
    # Note: activity_date and actor are automatically fetched from commit/pull_request tables

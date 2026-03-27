from fastapi import FastAPI

from routers.author_import.router import router as author_import_router
from routers.author_inject.router import router as author_inject_router
from routers.pull_request_import.router import router as pull_request_import_router
from routers.repo.router import router as repo_router
from routers.workspace.router import router as workspace_router
from routers.commit.router import router as commit_router
from routers.commit_files.router import router as commit_files_router
from routers.pr_update.router import router as pr_update_router
from routers.pr_reviewer.router import router as pr_reviewer_router
from routers.pr_comment.router import router as pr_comment_router
# from routers.pr_commit_relation.router import router as pr_commit_relation_router  # Module not found
from routers.health.router import router as health_router
from routers.change_requests.router import router as change_requests_router
from routers.deployment_frequency.router import router as deployment_frequency_router
from routers.lookup.router import router as lookup_router
# from routers.cursor_daily_usage.router import router as cursor_daily_usage_router  # Module not found
# from routers.cursor_spending.router import router as cursor_spending_router  # Module not found
from routers.jira_import.router import router as jira_import_router

app = FastAPI(title="Author Import API")
app.include_router(author_import_router)
app.include_router(author_inject_router)
app.include_router(pull_request_import_router)
app.include_router(workspace_router)
app.include_router(repo_router)
app.include_router(commit_router)
app.include_router(commit_files_router)
app.include_router(pr_update_router)
app.include_router(pr_reviewer_router)
app.include_router(pr_comment_router)
# app.include_router(pr_commit_relation_router)  # Module not found
app.include_router(health_router)
app.include_router(change_requests_router)
app.include_router(deployment_frequency_router)
# app.include_router(cursor_daily_usage_router)  # Module not found
# app.include_router(cursor_spending_router)  # Module not found
app.include_router(jira_import_router)
app.include_router(lookup_router)

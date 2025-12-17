from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from routers.author_import.router import router as author_import_router
from routers.pull_request_import.router import router as pull_request_import_router
from routers.repo.router import router as repo_router
from routers.workspace.router import router as workspace_router
from db.session import get_db_session

app = FastAPI(title="Author Import API")
app.include_router(author_import_router)
app.include_router(pull_request_import_router)
app.include_router(workspace_router)
app.include_router(repo_router)


@app.get("/healthz", tags=["health"])
def healthcheck(session: Session = Depends(get_db_session)):
    session.execute(text("SELECT 1"))
    return {"status": "ok"}

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.session import get_db_session
from schemas.health import DatabaseHealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "/database",
    summary="Check database connectivity",
    response_model=DatabaseHealthResponse,
)
def database_health(session: Session = Depends(get_db_session)) -> DatabaseHealthResponse:
    session.execute(text("SELECT 1"))
    return DatabaseHealthResponse(status="ok")

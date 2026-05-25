from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
import os

from db.session import get_db_session
from schemas.health import DatabaseHealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "/database",
    summary="Check database connectivity and show connection details",
    response_model=DatabaseHealthResponse,
)
def database_health(session: Session = Depends(get_db_session)) -> DatabaseHealthResponse:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {exc}",
        ) from exc
    
    # Get database connection details from environment variables
    host = os.getenv("host", "unknown")
    port = os.getenv("port", "5432")
    database = os.getenv("engine", "unknown")
    username = os.getenv("username", "unknown")
    
    return DatabaseHealthResponse(
        status="ok",
        host=host,
        port=port,
        database=database,
        username=username,
    )

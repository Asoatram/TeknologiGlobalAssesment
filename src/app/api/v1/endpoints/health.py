from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import check_db_connection

router = APIRouter()


@router.get("/health", summary="Health check")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db", summary="Database connectivity health check")
def database_health_check() -> dict[str, str]:
    try:
        check_db_connection()
        return {"status": "ok"}
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable")

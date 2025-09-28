from typing import Optional
from fastapi import APIRouter
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from config.config_database import get_db
from schemas.os import OsCreate, OsListResponse, OsResponse, OsSearchParams, OsUpdate
from services.os_service import OsService
from utils.auth import require_admin, require_user


router = APIRouter(prefix="/api/os_version", tags=["OS Version"])


def get_os_service(db : Session = Depends(get_db)) -> OsService:
    return OsService(db)



@router.get("/", response_model=OsListResponse)
def get_os_versions(
    keyword: str = Query(None, max_length=255, description="version of os"),
    page: int = Query(1, ge=1, description="current page"),
    page_size: int = Query(10, ge=1, le=100, description="page size"),
    os_service: OsService = Depends(get_os_service),
    current_user = Depends(require_user())
):
    try:
        search_params = OsSearchParams(
            keyword=keyword,
            page=page,
            size=page_size
        )
        print("Debug: search_params =", search_params)
        return os_service.search(search_params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{os_id}", response_model=OsResponse)
def get_os_by_id(
    os_id: int,
    os_service: OsService = Depends(get_os_service),
    current_user = Depends(require_user())
):
    try:
        os = os_service.get_by_id(os_id)
        if not os:
            raise HTTPException(status_code=404, detail="OS not found")
        return os
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    keyword: str = Query(None, max_length=255, description="Tên hệ điều hành để tìm kiếm"),
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    page_size: int = Query(10, ge=1, le=100, description="Số mục trên mỗi trang"),
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
            raise HTTPException(status_code=404, detail="Hệ điều hành không tìm thấy")
        return os
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/", response_model=OsResponse)
def create_os(
    os_create: OsCreate,
    os_service: OsService = Depends(get_os_service),
    current_user = Depends(require_admin())
):
    try:
        return os_service.create(os_create)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.put("/{os_id}", response_model=OsResponse)
def update_os(
    os_id: int,
    os_update: OsUpdate,
    os_service: OsService = Depends(get_os_service),
    current_user = Depends(require_admin())
):
    try:
        updated_os = os_service.update(os_update, os_id)
        if not updated_os:
            raise HTTPException(status_code=404, detail="Hệ điều hành không tìm thấy")
        return updated_os
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.delete("/{os_id}", response_model=dict)
def delete_os(
    os_id: int,
    os_service: OsService = Depends(get_os_service),
    current_user = Depends(require_admin())
):
    try:
        success = os_service.delete(os_id)
        if not success:
            raise HTTPException(status_code=404, detail="Hệ điều hành không tìm thấy")
        return {"detail": "Xóa hệ điều hành thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
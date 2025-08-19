from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from config.config_database import get_db
from schemas.connection import TestConnectionRequest, TestConnectionResponse
from services.connection_service import ConnectionService
from services.server_service import ServerService
from schemas.server import (
    ServerCreate,
    ServerUpdate,
    ServerResponse,
    ServerListResponse,
    ServerSearchParams
)

router = APIRouter(prefix="/servers", tags=["Servers"])


def get_server_service(db: Session = Depends(get_db)) -> ServerService:
    return ServerService(db)

def get_connection_service() -> ConnectionService:
    return ConnectionService()

@router.get("/", response_model=ServerListResponse)
def get_servers(
    keyword: Optional[str] = Query(None, description="Từ khóa tìm kiếm (để trống để lấy tất cả)"),
    workload_id: Optional[int] = Query(None, description="ID workload"),
    status: Optional[str] = Query(None, description="Trạng thái server"),
    page: int = Query(1, ge=1, description="Số trang"),
    page_size: int = Query(10, ge=1, le=100, description="Số lượng item mỗi trang"),
    server_service: ServerService = Depends(get_server_service)
):
    """Lấy danh sách server với tìm kiếm và lọc
    - Nếu keyword rỗng: trả về tất cả server
    - Nếu keyword có giá trị: tìm kiếm theo keyword
    """
    try:
        search_params = ServerSearchParams(
            keyword=keyword,
            workload_id=workload_id,
            status=status,
            page=page,
            size=page_size
        )
        return server_service.search_servers(search_params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))







@router.get("/{server_id}", response_model=ServerResponse)
def get_server_by_id(
    server_id: int,
    server_service: ServerService = Depends(get_server_service)
):
    """Lấy server theo ID"""
    try:
        server = server_service.get_server_by_id(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server không tìm thấy")
        return server
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=ServerResponse)
def create_server(
    server_data: ServerCreate,
    server_service: ServerService = Depends(get_server_service)
):
    """Tạo server mới"""
    try:
        return server_service.create_server(server_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{server_id}", response_model=ServerResponse)
def update_server(
    server_id: int,
    server_data: ServerUpdate,
    server_service: ServerService = Depends(get_server_service)
):
    """Cập nhật server"""
    try:
        server = server_service.update_server(server_id, server_data)
        if not server:
            raise HTTPException(status_code=404, detail="Server không tìm thấy")
        return server
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{server_id}")
def delete_server(
    server_id: int,
    server_service: ServerService = Depends(get_server_service)
):
    """Xóa server (hard delete vì model không có is_active)"""
    try:
        success = server_service.delete_server(server_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Server không tìm thấy")
        
        return {"message": "Xóa server thành công"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-connection", response_model=TestConnectionResponse)
def test_connections(
    request: TestConnectionRequest,
    connection_service: ConnectionService = Depends(get_connection_service)):

    try:
        if not request.servers:
            raise HTTPException(status_code=400, detail="Danh sách server không được rỗng")
        result = connection_service.test_multiple_connections(request)
        return result
        if len(request.servers) > 50:  # Giới hạn số lượng server test cùng lúc
            raise HTTPException(status_code=400, detail="Số lượng server tối đa là 50")


    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from config.config_database import get_db
from schemas.connection import ServerConnectionInfo, ServerConnectionResult, TestConnectionRequest, TestConnectionResponse
from services.connection_service import ConnectionService
from services.server_service import ServerService
from schemas.server import (
    ServerCreate,
    ServerUpdate,
    ServerResponse,
    ServerListResponse,
    ServerSearchParams
)

router = APIRouter(prefix="/api/servers", tags=["Servers"])


def get_server_service(db: Session = Depends(get_db)) -> ServerService:
    return ServerService(db)


def get_connection_service() -> ConnectionService:
    return ConnectionService()


@router.get("/", response_model=ServerListResponse)
def get_servers(
    keyword: Optional[str] = Query(None, description="Từ khóa tìm kiếm (để trống để lấy tất cả)"),
    workload_id: Optional[int] = Query(None, description="ID workload"),
    status: Optional[bool] = Query(None, description="Trạng thái server"),
    page: int = Query(1, ge=1, description="Số trang"),
    page_size: int = Query(10, ge=1, le=100, description="Số lượng item mỗi trang"),
    server_service: ServerService = Depends(get_server_service)
):
    
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
    
    try:
        return server_service.create_server(server_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=List[ServerResponse])
def create_servers_batch(
    servers: List[ServerCreate],  # Đổi từ ServerCreate thành ServerUploadItem
    server_service: ServerService = Depends(get_server_service)
):
    """
    Tạo nhiều servers từ danh sách ServerUploadItem (có workload_name)
    Sẽ convert workload_name thành workload_id trong service layer
    """
    try:
        if not servers:
            raise HTTPException(status_code=400, detail="Danh sách server không được rỗng")
        
        print(f"Received {len(servers)} servers to create")
        return server_service.create_servers_batch(servers)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{server_id}")
def delete_server(
    server_id: int,
    server_service: ServerService = Depends(get_server_service)
):
    
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
    connection_service: ConnectionService = Depends(get_connection_service)
):
    
    try:
        if not request.servers:
            raise HTTPException(status_code=400, detail="Danh sách server không được rỗng")
        if len(request.servers) > 50:  # Giới hạn số lượng server test cùng lúc
            raise HTTPException(status_code=400, detail="Số lượng server tối đa là 50")
        result = connection_service.test_multiple_connections(request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/test-single-connection", response_model=ServerConnectionResult)
def test_single_connection(
    server: ServerConnectionInfo, 
    connection_service: ConnectionService = Depends(get_connection_service)
):
    
    try:
        result = connection_service.test_single_connection(server)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.put("/{server_id}", response_model=ServerResponse)
def update_server(
    server_id: int,
    server_data: ServerUpdate,
    server_service: ServerService = Depends(get_server_service)
):
    """
    Cập nhật thông tin server bao gồm workload
    """
    try:
        updated_server = server_service.update_server(server_id, server_data)
        if not updated_server:
            raise HTTPException(status_code=404, detail="Server không tìm thấy")
        return updated_server
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/validate/hostname/{hostname}")
def validate_hostname(
    hostname: str,
    server_id: Optional[int] = Query(None, description="ID server để exclude (dành cho update)"),
    server_service: ServerService = Depends(get_server_service)
):
    """Kiểm tra hostname đã tồn tại hay chưa"""
    try:
        exists = server_service.check_hostname_exists(hostname, exclude_id=server_id)
        return {
            "hostname": hostname,
            "exists": exists,
            "valid": not exists,
            "message": "Hostname đã tồn tại" if exists else "Hostname có thể sử dụng"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/validate/ip/{ip_address}")
def validate_ip_address(
    ip_address: str,
    server_id: Optional[int] = Query(None, description="ID server để exclude (dành cho update)"),
    server_service: ServerService = Depends(get_server_service)
):
    """Kiểm tra IP address đã tồn tại hay chưa"""
    try:
        exists = server_service.check_ip_exists(ip_address, exclude_id=server_id)
        return {
            "ip_address": ip_address,
            "exists": exists,
            "valid": not exists,
            "message": "IP address đã tồn tại" if exists else "IP address có thể sử dụng"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


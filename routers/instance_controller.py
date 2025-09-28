from http import server
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from config.config_database import get_db
from schemas.connection import ServerConnectionInfo, ServerConnectionResult, TestConnectionRequest, TestConnectionResponse
from services.connection_service import ConnectionService
from services.instance_service import ServerService
from schemas.server import (
    ServerCreate,
    ServerUpdate,
    ServerResponse,
    ServerListResponse,
    ServerSearchParams
)
from utils.auth import require_admin, require_user

router = APIRouter(prefix="/api/servers", tags=["Servers"])


def get_server_service(db: Session = Depends(get_db)) -> ServerService:
    return ServerService(db)


def get_connection_service() -> ConnectionService:
    return ConnectionService()


@router.get("/", response_model=ServerListResponse)
def get_servers(
    keyword: Optional[str] = Query(None, description="keyword"),
    workload_id: Optional[int] = Query(None, description="ID workload"),
    status: Optional[bool] = Query(None, description="server search status"),
    page: int = Query(1, ge=1, description="Page"),
    page_size: int = Query(10, ge=1, le=100, description="Page size"),
    server_service: ServerService = Depends(get_server_service),
    current_user = Depends(require_user())
):
    
    try:
        if(current_user.role == 'admin'):
            search_params = ServerSearchParams(
                keyword=keyword,
                workload_id=workload_id,
                status=status,
                page=page,
                size=page_size
            )
        else:

            search_params = ServerSearchParams(
                keyword=keyword,
                workload_id=workload_id,
                status=status,
                page=page,
                size=page_size,
                user_id= current_user.id
            )
        return server_service.search_servers(search_params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{server_id}", response_model=ServerResponse)
def get_server_by_id(
    server_id: int,
    server_service: ServerService = Depends(get_server_service),
    current_user = Depends(require_user())
):
    
    try:
        if current_user.role == 'admin':
            server = server_service.get_server_by_id(server_id)
        else:
            server = server_service.get_server_by_id_and_user(server_id, current_user.id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        return server
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=ServerResponse)
def create_server(
    server_data: ServerCreate,
    server_service: ServerService = Depends(get_server_service),
    current_user = Depends(require_user())
):
    
    try:
        server_data.user_id = current_user.id
        return server_service.create(server_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=List[ServerResponse])
def create_servers_batch(
    servers: List[ServerCreate],  
    server_service: ServerService = Depends(get_server_service),
    current_user = Depends(require_user())
):
    
    try:
        if not servers:
            raise HTTPException(status_code=400, detail="List server is not empty")
        
        print(f"Received {len(servers)} servers to create")
        return server_service.create_batch(servers, current_user)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/test-connection", response_model=TestConnectionResponse)
def test_connections(
    request: TestConnectionRequest,
    connection_service: ConnectionService = Depends(get_connection_service),
    current_user = Depends(require_user())
):
    
    try:
        if not request.servers:
            raise HTTPException(status_code=400, detail="List server is not empty")
        result = connection_service.test_multiple_connections(request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/test-single-connection", response_model=ServerConnectionResult)
def test_single_connection(
    server: ServerConnectionInfo, 
    connection_service: ConnectionService = Depends(get_connection_service),
    current_user = Depends(require_user())
):
    
    try:
        result = connection_service.test_single_connection(server)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

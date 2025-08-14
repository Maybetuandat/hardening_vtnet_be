from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from config.config_database import get_db
from schemas.server_schemas import ServerCreate, ServerResponse, ServerUpdate
from services.server_service import ServerService

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/servers", tags=["Servers"])


@router.get("", response_model=List[ServerResponse])
async def get_all_servers(
    workload_id: int = Query(None, description="Filter by workload ID"),
    environment: str = Query(None, description="Filter by environment"),
    os_type: str = Query(None, description="Filter by OS type"),
    status: str = Query(None, description="Filter by status"),
    active_only: bool = Query(False, description="Get only active servers"),
    db: Session = Depends(get_db)
):
    """Get all servers with optional filtering"""
    try:
        if active_only:
            servers = ServerService.get_active_servers(db)
        elif workload_id:
            servers = ServerService.get_servers_by_workload(db, workload_id)
        elif environment:
            servers = ServerService.get_servers_by_environment(db, environment)
        elif os_type:
            servers = ServerService.get_servers_by_os_type(db, os_type)
        elif status:
            servers = ServerService.get_servers_by_status(db, status)
        else:
            servers = ServerService.get_all_servers(db)
        
        return servers
    except Exception as e:
        logger.error(f"Error fetching servers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch servers: {str(e)}"
        )


@router.get("/{server_id}", response_model=ServerResponse)
async def get_server(server_id: int, db: Session = Depends(get_db)):
    """Get server by ID"""
    try:
        server = ServerService.get_server_by_id(db, server_id)
        if not server:
            logger.warning(f"Server with ID {server_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Server not found"
            )
        return server
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching server: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch server: {str(e)}"
        )


@router.post("", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
async def create_server(server_data: ServerCreate, db: Session = Depends(get_db)):
    """Create a new server"""
    try:
        server = ServerService.create_server(db, server_data)
        logger.info(f"Server created successfully: {server.name}")
        return server
    except ValueError as e:
        logger.error(f"Validation error creating server: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating server: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create server: {str(e)}"
        )


@router.put("/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: int, 
    server_data: ServerUpdate, 
    db: Session = Depends(get_db)
):
    """Update an existing server"""
    try:
        updated_server = ServerService.update_server(db, server_id, server_data)
        if not updated_server:
            logger.warning(f"Server with ID {server_id} not found for update")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Server not found"
            )
        logger.info(f"Server with ID {server_id} updated successfully")
        return updated_server
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating server: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating server: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update server: {str(e)}"
        )


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(server_id: int, db: Session = Depends(get_db)):
    """Delete a server"""
    try:
        success = ServerService.delete_server(db, server_id)
        if not success:
            logger.warning(f"Server with ID {server_id} not found for deletion")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Server not found"
            )
        logger.info(f"Server with ID {server_id} deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting server: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete server: {str(e)}"
        )


@router.get("/workload/{workload_id}", response_model=List[ServerResponse])
async def get_servers_by_workload(workload_id: int, db: Session = Depends(get_db)):
    """Get all servers for a specific workload"""
    try:
        servers = ServerService.get_servers_by_workload(db, workload_id)
        return servers
    except Exception as e:
        logger.error(f"Error fetching servers by workload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch servers by workload: {str(e)}"
        )
@router.get("/workload/{workload_id}/count")
async def get_servers_by_workload(workload_id: int, db: Session = Depends(get_db)):
    """Get number of  servers for a specific workload"""
    try:
         counts = len(ServerService.get_servers_by_workload(db, workload_id))
         logger.info(f"Number of servers for workload {workload_id}: {counts}")
         return {"count": counts}
    except Exception as e:
        logger.error(f"Error fetching servers by workload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch servers by workload: {str(e)}"
        )
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from config.config_database import get_db
from schemas.workload_schemas import WorkloadCreate, WorkloadResponse, WorkloadUpdate
from services.workload_service import WorkloadService

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workloads", tags=["Workloads"])


@router.get("", response_model=List[WorkloadResponse])
async def get_all_workloads(
    workload_type: str = Query(None, description="Filter by workload type"),
    active_only: bool = Query(False, description="Get only active workloads"),
    db: Session = Depends(get_db)
):
    """Get all workloads with optional filtering"""
    try:
        if active_only:
            workloads = WorkloadService.get_active_workloads(db)
        elif workload_type:
            workloads = WorkloadService.get_workloads_by_type(db, workload_type)
        else:
            workloads = WorkloadService.get_all_workloads(db)
        
        return workloads
    except Exception as e:
        logger.error(f"Error fetching workloads: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch workloads: {str(e)}"
        )


@router.get("/{workload_id}", response_model=WorkloadResponse)
async def get_workload(workload_id: int, db: Session = Depends(get_db)):
    """Get workload by ID"""
    try:
        workload = WorkloadService.get_workload_by_id(db, workload_id)
        if not workload:
            logger.warning(f"Workload with ID {workload_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workload not found"
            )
        return workload
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching workload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch workload: {str(e)}"
        )


@router.post("", response_model=WorkloadResponse, status_code=status.HTTP_201_CREATED)
async def create_workload(workload_data: WorkloadCreate, db: Session = Depends(get_db)):
    """Create a new workload"""
    try:
        workload = WorkloadService.create_workload(db, workload_data)
        logger.info(f"Workload created successfully: {workload.name}")
        return workload
    except ValueError as e:
        logger.error(f"Validation error creating workload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating workload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workload: {str(e)}"
        )


@router.put("/{workload_id}", response_model=WorkloadResponse)
async def update_workload(
    workload_id: int, 
    workload_data: WorkloadUpdate, 
    db: Session = Depends(get_db)
):
    """Update an existing workload"""
    try:
        updated_workload = WorkloadService.update_workload(db, workload_id, workload_data)
        if not updated_workload:
            logger.warning(f"Workload with ID {workload_id} not found for update")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workload not found"
            )
        logger.info(f"Workload with ID {workload_id} updated successfully")
        return updated_workload
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating workload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating workload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update workload: {str(e)}"
        )


@router.delete("/{workload_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workload(workload_id: int, db: Session = Depends(get_db)):
    """Delete a workload"""
    try:
        success = WorkloadService.delete_workload(db, workload_id)
        if not success:
            logger.warning(f"Workload with ID {workload_id} not found for deletion")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workload not found"
            )
        logger.info(f"Workload with ID {workload_id} deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting workload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete workload: {str(e)}"
        )
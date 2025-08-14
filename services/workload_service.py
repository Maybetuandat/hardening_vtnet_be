from typing import List, Optional
from sqlalchemy.orm import Session
import logging

from dao.workload_dao import WorkloadDao
from models.workload import Workload
from schemas.workload_schemas import WorkloadCreate, WorkloadUpdate, WorkloadResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class WorkloadService:
    """Service layer for Workload operations"""

    @staticmethod
    def get_all_workloads(db: Session) -> List[WorkloadResponse]:
        """Get all workloads"""
        try:
            logger.info("Fetching all workloads from database")
            workloads = WorkloadDao.get_all_workloads(db)
            logger.info(f"Found {len(workloads)} workloads")
            return [WorkloadService._to_response(workload) for workload in workloads]
        except Exception as e:
            logger.error(f"Error fetching workloads: {str(e)}")
            raise

    @staticmethod
    def get_workload_by_id(db: Session, workload_id: int) -> Optional[WorkloadResponse]:
        """Get workload by ID"""
        try:
            logger.info(f"Fetching workload with ID: {workload_id}")
            workload = WorkloadDao.get_workload_by_id(db, workload_id)
            if workload:
                logger.info(f"Found workload: {workload.name}")
                return WorkloadService._to_response(workload)
            else:
                logger.warning(f"Workload with ID {workload_id} not found")
                return None
        except Exception as e:
            logger.error(f"Error fetching workload: {str(e)}")
            raise

    @staticmethod
    def create_workload(db: Session, workload_data: WorkloadCreate) -> WorkloadResponse:
        """Create a new workload"""
        try:
            logger.info(f"Creating new workload: {workload_data.name}")
            
            # Check if workload with same name already exists
            if WorkloadDao.exists_by_name(db, workload_data.name):
                raise ValueError(f"Workload with name '{workload_data.name}' already exists")
            
            workload = WorkloadDao.create_workload(db, workload_data)
            logger.info(f"Workload created successfully: {workload.name}")
            return WorkloadService._to_response(workload)
        except ValueError as e:
            logger.error(f"Validation error creating workload: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating workload: {str(e)}")
            raise

    @staticmethod
    def update_workload(db: Session, workload_id: int, workload_data: WorkloadUpdate) -> Optional[WorkloadResponse]:
        """Update an existing workload"""
        try:
            logger.info(f"Updating workload with ID: {workload_id}")
            
            # Check if workload exists
            existing_workload = WorkloadDao.get_workload_by_id(db, workload_id)
            if not existing_workload:
                logger.warning(f"Workload with ID {workload_id} not found for update")
                return None
            
            # Check if new name conflicts with existing workload (if name is being updated)
            if workload_data.name and workload_data.name != existing_workload.name:
                if WorkloadDao.exists_by_name_exclude_id(db, workload_data.name, workload_id):
                    raise ValueError(f"Workload with name '{workload_data.name}' already exists")
            
            updated_workload = WorkloadDao.update_workload(db, workload_id, workload_data)
            if updated_workload:
                logger.info(f"Workload updated successfully: {updated_workload.name}")
                return WorkloadService._to_response(updated_workload)
            return None
        except ValueError as e:
            logger.error(f"Validation error updating workload: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error updating workload: {str(e)}")
            raise

    @staticmethod
    def delete_workload(db: Session, workload_id: int) -> bool:
        """Delete a workload"""
        try:
            logger.info(f"Deleting workload with ID: {workload_id}")
            
            # Check if workload exists
            existing_workload = WorkloadDao.get_workload_by_id(db, workload_id)
            if not existing_workload:
                logger.warning(f"Workload with ID {workload_id} not found for deletion")
                return False
            
            success = WorkloadDao.delete_workload(db, workload_id)
            if success:
                logger.info(f"Workload with ID {workload_id} deleted successfully")
            return success
        except Exception as e:
            logger.error(f"Error deleting workload: {str(e)}")
            raise

    @staticmethod
    def get_workloads_by_type(db: Session, workload_type: str) -> List[WorkloadResponse]:
        """Get workloads by type"""
        try:
            logger.info(f"Fetching workloads of type: {workload_type}")
            workloads = WorkloadDao.get_workloads_by_type(db, workload_type)
            logger.info(f"Found {len(workloads)} workloads of type {workload_type}")
            return [WorkloadService._to_response(workload) for workload in workloads]
        except Exception as e:
            logger.error(f"Error fetching workloads by type: {str(e)}")
            raise

    @staticmethod
    def get_active_workloads(db: Session) -> List[WorkloadResponse]:
        """Get only active workloads"""
        try:
            logger.info("Fetching active workloads")
            workloads = WorkloadDao.get_active_workloads(db)
            logger.info(f"Found {len(workloads)} active workloads")
            return [WorkloadService._to_response(workload) for workload in workloads]
        except Exception as e:
            logger.error(f"Error fetching active workloads: {str(e)}")
            raise

    @staticmethod
    def _to_response(workload: Workload) -> WorkloadResponse:
        """Convert Workload model to WorkloadResponse"""
        return WorkloadResponse(
            id=workload.id,
            name=workload.name,
            display_name=workload.display_name,
            description=workload.description,
            workload_type=workload.workload_type,
            is_active=workload.is_active,
            created_at=workload.created_at,
            updated_at=workload.updated_at
        )
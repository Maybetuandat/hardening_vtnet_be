from typing import List, Optional
from sqlalchemy.orm import Session
from models.workload import Workload
from schemas.workload_schemas import WorkloadCreate, WorkloadUpdate


class WorkloadDao:
    """Data Access Object for Workload operations"""

    @staticmethod
    def get_all_workloads(db: Session) -> List[Workload]:
        """Get all workloads"""
        return db.query(Workload).all()

    @staticmethod
    def get_workload_by_id(db: Session, workload_id: int) -> Optional[Workload]:
        """Get workload by ID"""
        return db.query(Workload).filter(Workload.id == workload_id).first()

    @staticmethod
    def get_workload_by_name(db: Session, name: str) -> Optional[Workload]:
        """Get workload by name"""
        return db.query(Workload).filter(Workload.name == name).first()

    @staticmethod
    def exists_by_name(db: Session, name: str) -> bool:
        """Check if workload exists by name"""
        return db.query(Workload).filter(Workload.name == name).first() is not None

    @staticmethod
    def exists_by_name_exclude_id(db: Session, name: str, workload_id: int) -> bool:
        """Check if workload exists by name excluding specific ID"""
        return db.query(Workload).filter(
            Workload.name == name,
            Workload.id != workload_id
        ).first() is not None

    @staticmethod
    def create_workload(db: Session, workload_data: WorkloadCreate) -> Workload:
        """Create a new workload"""
        db_workload = Workload(
            name=workload_data.name,
            display_name=workload_data.display_name,
            description=workload_data.description,
            workload_type=workload_data.workload_type,
            is_active=workload_data.is_active
        )
        db.add(db_workload)
        db.commit()
        db.refresh(db_workload)
        return db_workload

    @staticmethod
    def update_workload(db: Session, workload_id: int, workload_data: WorkloadUpdate) -> Optional[Workload]:
        """Update an existing workload"""
        db_workload = db.query(Workload).filter(Workload.id == workload_id).first()
        if not db_workload:
            return None

        # Update only provided fields
        update_data = workload_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_workload, field, value)

        db.commit()
        db.refresh(db_workload)
        return db_workload

    @staticmethod
    def delete_workload(db: Session, workload_id: int) -> bool:
        """Delete a workload"""
        db_workload = db.query(Workload).filter(Workload.id == workload_id).first()
        if not db_workload:
            return False

        db.delete(db_workload)
        db.commit()
        return True

    @staticmethod
    def get_workloads_by_type(db: Session, workload_type: str) -> List[Workload]:
        """Get workloads by type"""
        return db.query(Workload).filter(Workload.workload_type == workload_type).all()

    @staticmethod
    def get_active_workloads(db: Session) -> List[Workload]:
        """Get only active workloads"""
        return db.query(Workload).filter(Workload.is_active == True).all()
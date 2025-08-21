from sqlalchemy.orm import Session
from typing import Optional, List, Tuple
from sqlalchemy.exc import IntegrityError

from models.workload import WorkLoad
class WorkLoadDAO:
    
    def __init__(self, db : Session):
        self.db = db 
    def get_workloads_with_pagination(self, skip: int = 0, limit: int = 10) -> Tuple[List[WorkLoad], int]:
        return self.search_workloads(skip=skip, limit=limit)
    def get_by_id(self, workload_id : int) -> Optional[WorkLoad]:
        return self.db.query(WorkLoad).filter(WorkLoad.id == workload_id).first()
    def get_by_name(self, name: str) -> Optional[WorkLoad]:
        return self.db.query(WorkLoad).filter(WorkLoad.name == name).first()
    def search_workloads(
        self,
        keyword: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[WorkLoad], int]:
        query = self.db.query(WorkLoad)
        
        if keyword and keyword.strip():
            query = query.filter(
                WorkLoad.name.ilike(f"%{keyword.strip()}%")
            )
        
        total = query.count()
        workloads = query.offset(skip).limit(limit).all()
        
        return workloads, total
    def create(self, workload: WorkLoad) -> WorkLoad:
        try:
            self.db.add(workload)
            self.db.commit()
            self.db.refresh(workload)
            return workload
        except IntegrityError as e:
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            raise e
    def update(self, workload: WorkLoad) -> WorkLoad:
        try:
            self.db.commit()
            self.db.refresh(workload)
            return workload
        except IntegrityError as e:
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            raise e
    def delete(self, workload: WorkLoad) -> None:
        try:
            self.db.delete(workload)
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            raise e
    def check_name_exists(self, name: str) -> bool:
        return self.db.query(WorkLoad).filter(WorkLoad.name == name).count() > 0
from datetime import datetime
from typing import Optional
from httpx import delete
from sqlalchemy.orm import Session

from models.os import Os
from models.workload import WorkLoad

class OsDao:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, os: Os) -> Os:
        try:
            self.db.add(os)
            self.db.commit()
            self.db.refresh(os)
            return os
        except Exception as e:
            self.db.rollback()
            raise e
    def get_by_id(self, os_id: int) -> Optional[Os]:
        return self.db.query(Os).filter(Os.id == os_id).first()
    def search(self, 
    
            keyword: Optional[str] = None, 
            offset: int = 0, 
            limit: int = 10, 
            ) -> tuple[list[Os], int]:
        query = self.db.query(Os)
       
        if keyword:
            query = query.filter(Os.version.ilike(f"%{keyword}%"))
        try:
            total = query.count()
            return query.offset(offset).limit(limit).all(), total
        except Exception as e:
            self.db.rollback()
            raise e
    def update(self, update_os: Os) -> Os:
        try:
            update_os.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(update_os)
            return update_os
        except Exception as e:
            self.db.rollback()
            raise e
    def delete(self, os_id: int) -> bool:
        try:
            os_to_delete = self.db.query(Os).filter(Os.id == os_id).first()
            if not os_to_delete:
                return False
            self.db.delete(os_to_delete)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e
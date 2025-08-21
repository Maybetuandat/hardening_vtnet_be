from sqlalchemy.orm import Session

from dao.workload_dao import WorkLoadDAO
class WorkloadService:
    def __init__(self, db: Session):
        self.dao = WorkLoadDAO(db)
    


    def get_all_workloads(self, page: int = 1, page_size: int = 10):
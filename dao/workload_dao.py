from sqlalchemy.orm import Session
class WorkLoadDAO:
    
    def __init__(self, db : Session):
        self.db = db 
    def 
from sqlalchemy.orm import Session
from typing import Optional, List, Tuple

from models.rule import Rule
class RuleDAO:
    def  __init__(self, db: Session):
        self.db = db
  
    def get_by_id(self, rule_id : int) -> Optional[Rule]:
        return self.db.query(Rule).filter(Rule.id == rule_id).first()
    def search_rules(
            self, 
            keyword: Optional[str] = None,
            skip : int = 0,
            limit : int = 10
    ) -> Tuple[List[Rule], int]:
        query = self.db.query(Rule)
        if keyword and keyword.strip():
            query = query.filter(
                Rule.name.ilike(f"%{keyword.strip()}%")
            )
        total = query.count()
        rules = query.offset(skip).limit(limit).all()
        return rules, total
    def create(self, rule: Rule) -> Rule:
        try:
            self.db.add(rule)
            self.db.commit()
            self.db.refresh(rule)
            return rule
        except InterruptedError as e: 
            self.db.rollback()
            raise e
    def update(self, rule : Rule) -> Rule:
        try:
            self.db.commit()
            self.db.refresh(rule)
            return rule
        except InterruptedError as e: 
            self.db.rollback()
            raise e

    def delete(self, rule: Rule) -> None:
        try:
            self.db.delete(rule)
            self.db.commit()
        except InterruptedError as e: 
            self.db.rollback()
            raise e 
        except Exception as e :
            self.db.rollback()
            raise e
    def get_rules_with_workload_id(
            self, 
            workload_id: int, 
            skip: int = 0, 
            limit: int = 10
    ) -> Tuple[List[Rule], int]:
        query = self.db.query(Rule).filter(Rule.workload_id == workload_id)
        total = query.count()
        rules = query.offset(skip).limit(limit).all()
        return rules, total
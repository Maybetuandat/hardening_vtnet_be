from sqlalchemy.orm import Session
from typing import Optional, List, Tuple

from models.rule import Rule
class RuleDAO:
    def  __init__(self, db: Session):
        self.db = db
  
    def get_by_id(self, rule_id : int) -> Optional[Rule]:
        return self.db.query(Rule).filter(Rule.id == rule_id).first()
    def get_active_rules_by_workload_id(self, workload_id: int) -> List[Rule]:
        return self.db.query(Rule).filter(Rule.workload_id == workload_id, Rule.is_active == True).all()
    
    def create_bulk(self, rules: List[Rule]) -> List[Rule]:
        try:
            self.db.add_all(rules) 
            self.db.commit()
            for rule in rules:
                self.db.refresh(rule)
            return rules
        except Exception as e:
            self.db.rollback()
            raise e

    def search_rules(
            self, 
            keyword: Optional[str] = None,
            workload_id: Optional[int] = None,
            skip : int = 0,
            limit : int = 10
    ) -> Tuple[List[Rule], int]:
        query = self.db.query(Rule)
        if workload_id is not None and workload_id > 0:
            query = query.filter(Rule.workload_id == workload_id)
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
   
from sqlalchemy.orm import Session
from typing import Optional, List
from dao.rule_dao import RuleDAO
from models.rule import Rule
from schemas.rule import RuleCreate, RuleUpdate, RuleResponse, RuleListResponse, RuleSearchParams
import math

class RuleService:
    def __init__(self, db: Session):
        self.rule_dao = RuleDAO(db)
    
    def get_rules_with_pagination(self, page: int = 1, page_size: int = 10) -> RuleListResponse:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100
            
        skip = (page - 1) * page_size
        rules, total = self.rule_dao.get_rules_with_pagination(skip=skip, limit=page_size)
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        
        rule_responses = []
        for rule in rules:
            rule_responses.append(self._convert_to_response(rule))
        
        return RuleListResponse(
            rules=rule_responses,
            total_rules=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
    def get_rule_by_id(self, rule_id: int) -> Optional[RuleResponse]:
        if rule_id <= 0:
            return None
        rule = self.rule_dao.get_by_id(rule_id)
        if rule:
            return self._convert_to_response(rule)
        return None
    
    def search_rules(self, search_params: RuleSearchParams) -> RuleListResponse:
        page = max(1, search_params.page)
        page_size = max(1, min(100, search_params.page_size))
            
        skip = (page - 1) * page_size
        rules, total = self.rule_dao.search_rules(
            keyword=search_params.keyword,
            workload_id=search_params.workload_id,
            severity=search_params.severity,
            skip=skip,
            limit=page_size
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        
        rule_responses = []
        for rule in rules:
            rule_responses.append(self._convert_to_response(rule))
        
        return RuleListResponse(
            rules=rule_responses,
            total_rules=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
    def create_rule(self, rule_data: RuleCreate) -> RuleResponse:
        try:
            self._validate_rule_create_data(rule_data)
            
            rule_dict = rule_data.dict()
            rule_model = Rule(**rule_dict)
            
            created_rule = self.rule_dao.create(rule_model)
            return self._convert_to_response(created_rule)
            
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(f"Lỗi khi tạo rule: {str(e)}")
    
    def update_rule(self, rule_id: int, rule_data: RuleUpdate) -> Optional[RuleResponse]:
        try:
            if rule_id <= 0:
                return None
                
            existing_rule = self.rule_dao.get_by_id(rule_id)
            if not existing_rule:
                return None
                
            self._validate_rule_update_data(rule_data)
            
            update_data = rule_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(existing_rule, field) and value is not None:
                    setattr(existing_rule, field, value)
            
            updated_rule = self.rule_dao.update(existing_rule)
            return self._convert_to_response(updated_rule)
            
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(f"Lỗi khi cập nhật rule: {str(e)}")
    
    def delete_rule(self, rule_id: int) -> bool:
        try:
            if rule_id <= 0:
                return False
                
            existing_rule = self.rule_dao.get_by_id(rule_id)
            if not existing_rule:
                return False
            
            self.rule_dao.delete(existing_rule)
            return True
            
        except Exception as e:
            raise Exception(f"Lỗi khi xóa rule: {str(e)}")
    
    def _convert_to_response(self, rule: Rule) -> RuleResponse:
        return RuleResponse(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            severity=rule.severity,
            workload_id=rule.workload_id,
            parameters=rule.parameters,
            is_active=rule.is_active,
            created_at=rule.created_at,
            updated_at=rule.updated_at
        )
    
    def _validate_rule_create_data(self, rule_data: RuleCreate) -> None:
        if not rule_data.name or not rule_data.name.strip():
            raise ValueError("Tên rule không được để trống")
            
        if not rule_data.severity or rule_data.severity not in ["low", "medium", "high", "critical"]:
            raise ValueError("Severity phải là một trong: low, medium, high, critical")
            
        if rule_data.workload_id and rule_data.workload_id <= 0:
            raise ValueError("Workload ID phải lớn hơn 0")
    
    def _validate_rule_update_data(self, rule_data: RuleUpdate) -> None:
        if rule_data.name is not None and (not rule_data.name or not rule_data.name.strip()):
            raise ValueError("Tên rule không được để trống")
            
        if rule_data.severity is not None and rule_data.severity not in ["low", "medium", "high", "critical"]:
            raise ValueError("Severity phải là một trong: low, medium, high, critical")
            
        if rule_data.workload_id is not None and rule_data.workload_id <= 0:
            raise ValueError("Workload ID phải lớn hơn 0")
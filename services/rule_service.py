from datetime import datetime
import json
from numpy import sort
from sqlalchemy.orm import Session
from typing import Dict, Optional, List
from dao.rule_dao import RuleDAO
from models.rule import Rule
from schemas.rule import RuleCheckResult, RuleCreate, RuleUpdate, RuleResponse, RuleListResponse, RuleSearchParams
import math

class RuleService:
    def __init__(self, db: Session):
        self.rule_dao = RuleDAO(db)
    
   
    
    def get_rule_by_id(self, rule_id: int) -> Optional[RuleResponse]:
        if rule_id <= 0:
            return None
        rule = self.rule_dao.get_by_id(rule_id)
        if rule:
            return self._convert_to_response(rule)
        return None
    
    def get_active_rule_by_workload(self, workload_id: int) -> List[RuleResponse]:
        if workload_id <= 0:
            return []
        rules = self.rule_dao.get_active_rules_by_workload_id(workload_id)
        return [self._convert_to_response(rule) for rule in rules]
    def search_rules(self, search_params: RuleSearchParams) -> RuleListResponse:
        page = max(1, search_params.page)
        page_size = max(1, min(100, search_params.page_size))
            
        skip = (page - 1) * page_size
    
        rules, total = self.rule_dao.search_rules(
                workload_id=search_params.workload_id,
                keyword=search_params.keyword,
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
    
    def create(self, rule_data: RuleCreate) -> RuleResponse:
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
    def create_bulk(self, rules_data: List[RuleCreate]) -> List[RuleResponse]:
        try:
            if not rules_data or len(rules_data) == 0:
                return []
            
            created_rules = []
            for rule_data in rules_data:
                self._validate_rule_create_data(rule_data)
                rule_dict = rule_data.dict()
                rule_model = Rule(**rule_dict)
                created_rules.append(rule_model)
               
            list_rule_creates = self.rule_dao.create_bulk(created_rules)
            return [self._convert_to_response(rule) for rule in list_rule_creates]
            
            
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(f"Lỗi khi tạo bulk rules: {str(e)}")
    def update_with_role_admin(self, rule_id: int, rule_data: RuleUpdate) -> Optional[RuleResponse]:
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
    

    def update_with_role_user(self, rule_id: int, rule_data: RuleUpdate) -> Optional[RuleResponse]:
        try:
            if rule_id <= 0: 
                return None 
            existing_rule = self.rule_dao.get_by_id(rule_id)
            if not existing_rule:
                return None
            if existing_rule.role_can_request_edit == 'admin':
                # create a copy of rule 
                if existing_rule.can_be_copied:
                    copyrule = Rule(
                    name=rule_data.name if rule_data.name is not None else existing_rule.name,
                    description=rule_data.description if rule_data.description is not None else existing_rule.description,
                    command=rule_data.command if rule_data.command is not None else existing_rule.command,
                    workload_id=rule_data.workload_id if rule_data.workload_id is not None else existing_rule.workload_id,
                    parameters=rule_data.parameters if rule_data.parameters is not None else existing_rule.parameters,
                    is_active="pending",
                    role_can_request_edit='user',
                    copied_from_id=existing_rule.id
                    )
                    created_rule = self.rule_dao.create(copyrule)
                    existing_rule.can_be_copied = False
                    self.rule_dao.update(existing_rule)
                    return self._convert_to_response(created_rule)
                else:
                    raise ValueError("Please wait for admin to update this rule")
            else:
                self._validate_rule_update_data(rule_data)
                update_data = rule_data.dict(exclude_unset=True)
                for field, value in update_data.items():
                    if hasattr(existing_rule, field) and value is not None:
                        setattr(existing_rule, field, value)
                existing_rule.is_active = "pending"
                updated_rule = self.rule_dao.update(existing_rule)
                return self._convert_to_response(updated_rule)
        except ValueError as e:
            raise ValueError(str(e))
    def delete(self, rule_id: int) -> bool:
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
            command=rule.command,
            workload_id=rule.workload_id,
            parameters=rule.parameters,
            is_active=rule.is_active,
            created_at=rule.created_at,
            updated_at=rule.updated_at,
            can_be_copied=rule.can_be_copied
        )
    
    def _validate_rule_create_data(self, rule_data: RuleCreate) -> None:
        if not rule_data.name or not rule_data.name.strip():
            raise ValueError("Rule name is not allowed to be empty")
            
       
        if rule_data.workload_id and rule_data.workload_id <= 0:
            raise ValueError("Workload ID must be greater than 0")
    
    def _validate_rule_update_data(self, rule_data: RuleUpdate) -> None:
        if rule_data.name is not None and (not rule_data.name or not rule_data.name.strip()):
            raise ValueError("Rule name is not allowed to be empty")
             
        if rule_data.workload_id is not None and rule_data.workload_id <= 0:
            raise ValueError("Workload ID must be greater than 0")
   

    def check_rules_existence_in_workload(self, workload_id: int, rules_to_check: List[RuleCreate]) -> List[RuleCheckResult]:
        
        try:
            
            if workload_id <= 0:
                raise ValueError("Workload ID must be greater than 0")
            
            if not rules_to_check or len(rules_to_check) == 0:
                return []
            
            
            existing_rules = self.rule_dao.get_active_rules_by_workload_id(workload_id)
            
            
            existing_names = set()
            existing_param_hashes = set()
            
            for existing_rule in existing_rules:
               
                existing_names.add(existing_rule.name.lower().strip())
                
               
                param_hash = self._create_parameter_hash(existing_rule.parameters)
                if param_hash:
                    existing_param_hashes.add(param_hash)
            
            
            results = []
            
            for rule_input in rules_to_check:
                rule_name = rule_input.name.lower().strip()
                rule_parameters = rule_input.parameters
                
                is_duplicate = False
                duplicate_reason = None
                
                # Kiểm tra trùng tên
                if rule_name in existing_names:
                    is_duplicate = True
                    duplicate_reason = 'name'
                
                # Kiểm tra trùng hash parameter )
                if not is_duplicate:
                    input_param_hash = self._create_parameter_hash(rule_parameters)
                    if input_param_hash in existing_param_hashes:
                        is_duplicate = True
                        duplicate_reason = 'parameter_hash'
                
                result = RuleCheckResult(
                    name=rule_input.name,
                    description=rule_input.description,
                    parameters=rule_input.parameters,
                    workload_id=rule_input.workload_id,
                    is_active=rule_input.is_active,
                    is_duplicate=is_duplicate,
                    duplicate_reason=duplicate_reason, 
                    command=rule_input.command
                )
                
                
                results.append(result)
            
            return results
            
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise Exception(f"Lỗi khi kiểm tra rule existence: {str(e)}")

    def _create_parameter_hash(self, parameters):
       
        if not parameters:
            return None
        
        try:
            normalized_json = json.dumps(parameters, sort_keys=True, separators=(',', ':'))
            return normalized_json
            
        except (json.JSONDecodeError, TypeError):
            
            return str(parameters)
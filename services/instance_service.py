from re import search
from typing import Any, Dict, List, Optional
from venv import create
from sqlalchemy import Boolean
from sqlalchemy.orm import Session
from dao.instance_dao import InstanceDAO
from dao.workload_dao import WorkLoadDAO
from models.instance import Instance
from models.user import User
from schemas.instance import (
    InstanceCreate, 
    InstanceUpdate, 
    InstanceResponse, 
    InstanceListResponse, 
    InstanceSearchParams
)
import math
from sqlalchemy.exc import IntegrityError



class InstanceService:
    def __init__(self, db: Session):
        self.dao = InstanceDAO(db)
        self.workload_dao = WorkLoadDAO(db)


  

    def get_instance_by_id(self, instance_id: int) -> Optional[InstanceResponse]:
        if instance_id <= 0:
            return None
            
        instance = self.dao.get_by_id(instance_id)
        if instance:
            return self._convert_to_response(instance)
        return None

    def get_instance_by_id_and_user(self, instance_id: int, user_id: int) -> Optional[InstanceResponse]:
        if instance_id <= 0 or user_id <= 0:
            return None

        instance = self.dao.get_by_id_instance_and_id_user(instance_id, user_id)
        if instance:
            return self._convert_to_response(instance)
        return None
    def search_instances(self, search_params: InstanceSearchParams) -> InstanceListResponse:
        page = max(1, search_params.page)
        page_size = max(1, min(100, search_params.size))  
        
        skip = (page - 1) * page_size

        instances, total = self.dao.search_instances(
            keyword=search_params.keyword,
            workload_id=search_params.workload_id,
            status=search_params.status,
            skip=skip,
            limit=page_size, 
            user_id = search_params.user_id
        )
        
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        instance_responses = []
        for instance in instances:
            instance_responses.append(self._convert_to_response(instance))

        return InstanceListResponse(
            instances=instance_responses,
            total_instances=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
   

    

    def create(self, instance_data: InstanceCreate) -> InstanceResponse:
        try:
            


            if self.dao.check_ip_address_exists(instance_data.name):
                raise ValueError("Ip address exists")



            instance_dict = instance_data.dict()
            instance_model = Instance(**instance_dict)
            
            
            created_instance = self.dao.create(instance_model)
            
            return self._convert_to_response(created_instance)
            
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(f"failed to create instance: {str(e)}")

   
   

    def update(self, instance_data : InstanceUpdate, instance_id : int) -> InstanceResponse:
        try:
            if instance_id <= 0:
                raise ValueError("Invalid instance id")
                
            existing_instance = self.dao.get_by_id(instance_id)
            if not existing_instance:
                raise ValueError("Instance is not found")
                
            if instance_data.name and self.dao.check_ip_address_exists(instance_data.name, exclude_id=instance_id):
                raise ValueError("Ip address exists")
                
            for field, value in instance_data.dict(exclude_unset=True).items():
                setattr(existing_instance, field, value)
                
            updated_instance = self.dao.update(existing_instance)
            return self._convert_to_response(updated_instance)
            
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(f"Failed to update instance: {str(e)}")
    def delete(self, instance_id: int) -> bool:
        try:
            if instance_id <= 0:
                return False
                
            
            existing_instance = self.dao.get_by_id_instance_and_id_user(instance_id)
            if not existing_instance:
                raise ValueError("Instance is not found or you do not have permission to delete this instance")
                

            return self.dao.delete(existing_instance)
            
        except Exception as e:
            raise Exception(f"Failed to delete  instance: {str(e)}")

   
        
    def assign_instances_to_workload(
        self,
        workload_id: int,
        instance_ids: List[int]
    ) -> Dict[str, Any]:
        
        try:
            # Kiểm tra workload tồn tại
            workload = self.workload_dao.get_by_id(workload_id)
            if not workload:
                raise ValueError(f"Workload with id {workload_id} not found")
            
            if not instance_ids or len(instance_ids) == 0:
                raise ValueError("Instance IDs list cannot be empty")
            
            assigned_count = 0
            for instance_id in instance_ids:
                instance = self.dao.get_by_id(instance_id)
                if instance:
                    instance.workload_id = workload_id
                    self.dao.update(instance)
                    assigned_count += 1
            return {
                "workload_id": workload_id,
                "assigned_count": assigned_count,
                "failed_ids": []
            }
            
        except ValueError as e:
           
            raise e
        except Exception as e:
           
            raise Exception(f"Error assigning instances to workload: {str(e)}")
    
    
    def remove_workload_from_instances(
        self,
        workload_id: int,
        instance_ids: List[int]
    ) -> int:
       
        try:
            # Kiểm tra workload tồn tại
            workload = self.workload_dao.get_by_id(workload_id)
            if not workload:
                raise ValueError(f"Workload with id {workload_id} not found")
            
            if not instance_ids or len(instance_ids) == 0:
                raise ValueError("Instance IDs list cannot be empty")
            result  = 0
            for instance_id in instance_ids:
                instance = self.dao.get_by_id(instance_id)
                if instance and instance.workload_id == workload_id:
                    instance.workload_id = None
                    self.dao.update(instance)
                    result += 1
            
            return result
            
        except ValueError as e:
           
            raise e
        except Exception as e:
           
            raise Exception(f"Error removing workload from instances: {str(e)}")
    def _convert_to_response(self, instance: Instance) -> InstanceResponse:
        workload = self.workload_dao.get_by_id(instance.workload_id)
        return InstanceResponse(
            id=instance.id,
            name=instance.name,
            status=instance.status,
            workload_name=workload.name if workload else None,
            ssh_port=instance.ssh_port,
            workload_id=instance.workload_id,
            created_at=instance.created_at,
            updated_at=instance.updated_at,
            nameofmanager=instance.user.username if instance.user else None
        )


  
        

  
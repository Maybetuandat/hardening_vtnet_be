from datetime import datetime
import logging
from fastapi import logger
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func
from typing import Any, Dict, Optional, List, Tuple
from models.instance import Instance
from schemas.instance import InstanceCreate, InstanceUpdate


class InstanceDAO:
    def __init__(self, db: Session):
        self.db = db


    def get_instances(self, skip: int, limit: int, current_user_id: Optional[int], is_has_workload: Optional[bool]) -> List[Instance]:
        query = self.db.query(Instance)
        if current_user_id:
            query = query.filter(Instance.user_id == current_user_id)
        if is_has_workload is not None:
            query = query.filter(Instance.workload_id != None) 
        query = query.offset(skip).limit(limit)
        return query.all()



    def get_all_instances(self) -> List[Instance]:
        try:
            return self.db.query(Instance).all()
        except Exception as e:
            logger.error(f"Error getting all instances: {str(e)}")
            return []

    def get_by_id(self, instance_id: int) -> Optional[Instance]:
        return self.db.query(Instance).filter(Instance.id == instance_id).first()

    def get_by_id_instance_and_id_user(self, instance_id: int, user_id: int) -> Optional[Instance]:
        return self.db.query(Instance).filter(and_(Instance.id == instance_id, Instance.user_id == user_id)).first()
    def search_instances(
        self,
        keyword: Optional[str] = None,
        workload_id: Optional[int] = None,
        status: Optional[bool] = None,
        skip: int = 0,
        limit: int = 10,
        user_id: Optional[int] = None,
        instance_not_in_workload: Optional[bool] = None
    ) -> Tuple[List[Instance], int]:
        query = self.db.query(Instance)
        
        if workload_id is not None:
            query = query.filter(Instance.workload_id == workload_id)
        if keyword and keyword.strip():
            query = query.filter(
                Instance.name.ilike(f"%{keyword.strip()}%")
            )
        if instance_not_in_workload is True:
            query = query.filter(Instance.workload_id == None)
        if user_id is not None:
            query = query.filter(Instance.user_id == user_id)
        if status is not None:
            query = query.filter(Instance.status == status)
        
        total = query.count()
        instances = query.offset(skip).limit(limit).all()
        
        return instances, total

    def create(self, instance: Instance) -> Instance:
        try:    
            self.db.add(instance)
            self.db.commit()
            self.db.refresh(instance)
            return instance
            
        except IntegrityError as e:
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            raise e

    def update(self, instance: Instance) -> Instance:
        try:
            instance.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(instance)
            return instance
            
        except IntegrityError as e:
            self.db.rollback()
            if "name" in str(e.orig):
                raise ValueError("Ip address exists")
            else:
                raise ValueError("Invalid data")
        except Exception as e:
            self.db.rollback()
            raise e
    

    def create_batch(self, instances: List[Instance]) -> List[Instance]:
        self.db.add_all(instances)
        self.db.commit()
        return instances

    def delete(self, instance: Instance) -> bool:
        try:
            self.db.delete(instance)
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            raise e

    
    def check_ip_address_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        query = self.db.query(Instance).filter(Instance.name == name)

        if exclude_id:
            query = query.filter(Instance.id != exclude_id)
            
        return query.first() is not None

    
    


    


   

   

    
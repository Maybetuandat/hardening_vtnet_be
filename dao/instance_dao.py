from datetime import datetime
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func
from typing import Any, Dict, Optional, List, Tuple
from models.instance import Server
from schemas.server import ServerCreate, ServerUpdate


class ServerDAO:
    def __init__(self, db: Session):
        self.db = db

   
    def get_servers(self, skip : int, limit: int) -> List[Server]:
        return self.db.query(Server).offset(skip).limit(limit).all()



 

    def get_by_id(self, server_id: int) -> Optional[Server]:
        return self.db.query(Server).filter(Server.id == server_id).first()

    def get_by_id_server_and_id_user(self, server_id: int, user_id: int) -> Optional[Server]:
        return self.db.query(Server).filter(and_(Server.id == server_id, Server.user_id == user_id)).first()
    def search_servers(
        self,
        keyword: Optional[str] = None,
        workload_id: Optional[int] = None,
        status: Optional[bool] = None,
        skip: int = 0,
        limit: int = 10,
        user_id: Optional[int] = None
    ) -> Tuple[List[Server], int]:
        query = self.db.query(Server)
        
        if keyword and keyword.strip():
            query = query.filter(
                or_(
                    Server.ip_address.ilike(f"%{keyword.strip()}%"),
                    Server.hostname.ilike(f"%{keyword.strip()}%")
                )
            )
        
        if user_id is not None:
            query = query.filter(Server.user_id == user_id)
        if status is not None:
            query = query.filter(Server.status == status)
        
        total = query.count()
        servers = query.offset(skip).limit(limit).all()
        
        return servers, total

    def create(self, server: Server) -> Server:
        try:    
            self.db.add(server)
            self.db.commit()
            self.db.refresh(server)
            return server
            
        except IntegrityError as e:
            self.db.rollback()
            raise e
        except Exception as e:
            self.db.rollback()
            raise e

    def update(self, server: Server) -> Server:
        try:
            server.updated_at = datetime.now()
            self.db.commit()
            self.db.refresh(server)
            return server
            
        except IntegrityError as e:
            self.db.rollback()
            if "hostname" in str(e.orig):
                raise ValueError("Hostname exists")
            elif "ip_address" in str(e.orig):
                raise ValueError("IP address exists")
            else:
                raise ValueError("Invalid data")
        except Exception as e:
            self.db.rollback()
            raise e
    

    def create_batch(self, servers: List[Server]) -> List[Server]:
        self.db.add_all(servers)   
        return servers
    def delete(self, server: Server) -> bool:
        try:
            self.db.delete(server)
            self.db.delete(server)
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            raise e

    
    def check_name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        query = self.db.query(Server).filter(Server.name == name)

        if exclude_id:
            query = query.filter(Server.id != exclude_id)
            
        return query.first() is not None

    
    


    


   

   

    
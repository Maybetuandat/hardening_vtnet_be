import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func
from typing import Any, Dict, Optional, List, Tuple
from models.server import Server
from schemas.server import ServerCreate, ServerUpdate


class ServerDAO:
    def __init__(self, db: Session):
        self.db = db

   
    def get_active_servers(self, skip : int, limit: int) -> List[Server]:
        return self.db.query(Server).offset(skip).limit(limit).all()



 

    def get_by_id(self, server_id: int) -> Optional[Server]:
        return self.db.query(Server).filter(Server.id == server_id).first()


    def search_servers(
        self,
        keyword: Optional[str] = None,
        workload_id: Optional[int] = None,
        status: Optional[bool] = None,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[Server], int]:
        query = self.db.query(Server)
        
        if keyword and keyword.strip():
            query = query.filter(
                or_(
                    Server.ip_address.ilike(f"%{keyword.strip()}%"),
                    Server.hostname.ilike(f"%{keyword.strip()}%")
                )
            )
        
        
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
            self.db.commit()
            self.db.refresh(server)
            return server
            
        except IntegrityError as e:
            self.db.rollback()
            if "hostname" in str(e.orig):
                raise ValueError("Hostname đã tồn tại")
            elif "ip_address" in str(e.orig):
                raise ValueError("IP address đã tồn tại")
            else:
                raise ValueError("Dữ liệu không hợp lệ")
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

    
    def check_hostname_exists(self, hostname: str, exclude_id: Optional[int] = None) -> bool:
        query = self.db.query(Server).filter(Server.hostname == hostname)
        
        if exclude_id:
            query = query.filter(Server.id != exclude_id)
            
        return query.first() is not None

    
    def check_ip_exists(self, ip_address: str, exclude_id: Optional[int] = None) -> bool:
        query = self.db.query(Server).filter(Server.ip_address == ip_address)
        
        if exclude_id:
            query = query.filter(Server.id != exclude_id)
            
        return query.first() is not None
    



    


   

   

    
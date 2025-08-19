from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func
from typing import Optional, List, Tuple
from models.server import Server
from schemas.server import ServerCreate, ServerUpdate


class ServerDAO:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 10) -> Tuple[List[Server], int]:
        return self.search_servers(skip=skip, limit=limit)

    def get_by_id(self, server_id: int) -> Optional[Server]:
        return self.db.query(Server).filter(Server.id == server_id).first()

    def get_by_hostname(self, hostname: str) -> Optional[Server]:
        return self.db.query(Server).filter(Server.hostname == hostname).first()

    def get_by_ip_address(self, ip_address: str) -> Optional[Server]:
        return self.db.query(Server).filter(Server.ip_address == ip_address).first()

    def search_servers(
        self,
        keyword: Optional[str] = None,
        workload_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[Server], int]:
    
        query = self.db.query(Server)
        if keyword and keyword.strip():
            query = query.filter(Server.ip_address.ilike(f"%{keyword.strip()}%"))
        
        # Filter theo status
        if status and status.strip():
            query = query.filter(Server.status == status.strip())
        
        total = query.count()
        
    
        servers = query.offset(skip).limit(limit).all()
        
        return servers, total

    def create(self, server_data: ServerCreate) -> Server:
     
        # Kiểm tra hostname đã tồn tại
        existing_hostname = self.get_by_hostname(server_data.hostname)
        if existing_hostname:
            raise ValueError("Hostname đã tồn tại")
        
        # Kiểm tra IP đã tồn tại
        existing_ip = self.get_by_ip_address(server_data.ip_address)
        if existing_ip:
            raise ValueError("IP address đã tồn tại")
        
        # Tạo server mới - chỉ sử dụng các field có trong schema
        server_dict = server_data.dict()
        db_server = Server(**server_dict)
        
        self.db.add(db_server)
        self.db.commit()
        self.db.refresh(db_server)
        return db_server

    def update(self, server_id: int, server_data: ServerUpdate) -> Optional[Server]:
        """Cập nhật server với validation"""
        server = self.get_by_id(server_id)
        if not server:
            return None
        
        # Kiểm tra hostname nếu có thay đổi
        if server_data.hostname and server_data.hostname != server.hostname:
            existing_hostname = self.get_by_hostname(server_data.hostname)
            if existing_hostname:
                raise ValueError("Hostname đã tồn tại")
        
        # Kiểm tra IP nếu có thay đổi
        if server_data.ip_address and server_data.ip_address != server.ip_address:
            existing_ip = self.get_by_ip_address(server_data.ip_address)
            if existing_ip:
                raise ValueError("IP address đã tồn tại")
        
        # Cập nhật các trường
        update_data = server_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(server, field):
                setattr(server, field, value)
        
        self.db.commit()
        self.db.refresh(server)
        return server

    def delete(self, server_id: int) -> bool:
        server = self.get_by_id(server_id)
        if not server:
            return False
        self.db.delete(server)
        self.db.commit()
        return True

  
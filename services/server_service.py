from re import search
from typing import List, Optional
from venv import create
from sqlalchemy import Boolean
from sqlalchemy.orm import Session
from dao.server_dao import ServerDAO
from dao.workload_dao import WorkLoadDAO
from models.server import Server
from models.user import User
from schemas.server import (
    ServerCreate, 
    ServerUpdate, 
    ServerResponse, 
    ServerListResponse, 
    ServerSearchParams
)
import math
from sqlalchemy.exc import IntegrityError



class ServerService:
    def __init__(self, db: Session):
        self.dao = ServerDAO(db)
        self.workload_dao = WorkLoadDAO(db)

  

    def get_server_by_id(self, server_id: int) -> Optional[ServerResponse]:
        if server_id <= 0:
            return None
            
        server = self.dao.get_by_id(server_id)
        if server:
            return self._convert_to_response(server)
        return None
   
    def get_server_by_id_and_user(self, server_id: int, user_id: int) -> Optional[ServerResponse]:
        if server_id <= 0 or user_id <= 0:
            return None

        server = self.dao.get_by_id_server_and_id_user(server_id, user_id)
        if server:
            return self._convert_to_response(server)
        return None
    def search_servers(self, search_params: ServerSearchParams) -> ServerListResponse:
        page = max(1, search_params.page)
        page_size = max(1, min(100, search_params.size))  
        
        skip = (page - 1) * page_size
        
        servers, total = self.dao.search_servers(
            keyword=search_params.keyword,
            workload_id=search_params.workload_id,
            status=search_params.status,
            skip=skip,
            limit=page_size, 
            user_id = search_params.user_id
        )
        
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        
        server_responses = []
        for server in servers:
            server_responses.append(self._convert_to_response(server))
        
        return ServerListResponse(
            servers=server_responses,
            total_servers=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
   

    def update_status(self, id : int, status: Boolean):
        try:
            server = self.dao.get_by_id(id)
            server.status = status
            update_server = self.dao.update(server)
            return update_server
        except IntegrityError as e:
            self.dao.db.rollback()
            if "hostname" in str(e.orig):
                raise ValueError("Hostname đã tồn tại")
            elif "ip_address" in str(e.orig):
                raise ValueError("IP address đã tồn tại")
            else:
                raise ValueError("Dữ liệu không hợp lệ")
        except Exception as e:
            self.dao.db.rollback()
            raise e

    def create(self, server_data: ServerCreate) -> ServerResponse:
        try:
            
            self._validate_server_data(server_data)
            
            
            if self.dao.check_hostname_exists(server_data.hostname):
                raise ValueError("Hostname exists")
            
            
            if self.dao.check_ip_exists(server_data.ip_address):
                raise ValueError("IP address exists")

            server_dict = server_data.dict()
            server_model = Server(**server_dict)
            
            
            created_server = self.dao.create(server_model)
            
            return self._convert_to_response(created_server)
            
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(f"Lỗi khi tạo server: {str(e)}")

    def update(self, server_id: int, server_data: ServerUpdate, current_user: User) -> Optional[ServerResponse]:
        try:
            if server_id <= 0:
                return None
                
            # get server and check user has permission to update
            # current user is get from token
            existing_server = self.dao.get_by_id(server_id)
            if not existing_server:
                raise ValueError("Server is not found")

            if current_user.role == 'user':
                if existing_server.user_id != current_user.id:
                    raise ValueError("You do not have permission to update this server")  # user want to update server of another user 
                # case user want to change user_id
                if existing_server.user_id != server_data.user_id and server_data.user_id is not None:
                    raise ValueError("You do not have permission to change the user of this server") #user want to change user_id to another user 
            if server_data.hostname or server_data.ip_address:
                self._validate_update_data(server_data)

            # check hostname exists
            if server_data.hostname and server_data.hostname != existing_server.hostname:
                if self.dao.check_hostname_exists(server_data.hostname, exclude_id=server_id):
                    raise ValueError("Hostname exists")
            
            # check ip exists
            if server_data.ip_address and server_data.ip_address != existing_server.ip_address:
                if self.dao.check_ip_exists(server_data.ip_address, exclude_id=server_id):
                    raise ValueError("IP address exists")
            
            
            update_data = server_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(existing_server, field) and value is not None:
                    setattr(existing_server, field, value)
            
            
            updated_server = self.dao.update(existing_server)
            
            return self._convert_to_response(updated_server)
            
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(f"Lỗi khi cập nhật server: {str(e)}")

    def delete(self, server_id: int, current_user_id : int) -> bool:
        try:
            if server_id <= 0:
                return False
                
            
            existing_server = self.dao.get_by_id_server_and_id_user(server_id, current_user_id)
            if not existing_server:
                raise ValueError("Server is not found or you do not have permission to delete this server")
                

            return self.dao.delete(existing_server)
            
        except Exception as e:
            raise Exception(f"Failed to delete  server: {str(e)}")

    def check_server_exists(self, server_id: int) -> bool:
        if server_id <= 0:
            return False
        return self.dao.get_by_id(server_id) is not None

    def check_hostname_exists(self, hostname: str, exclude_id: Optional[int] = None) -> bool:
        if not hostname or not hostname.strip():
            return False
        return self.dao.check_hostname_exists(hostname.strip(), exclude_id)

    def check_ip_exists(self, ip_address: str, exclude_id: Optional[int] = None) -> bool:
        if not ip_address or not ip_address.strip():
            return False
        return self.dao.check_ip_exists(ip_address.strip(), exclude_id)

   







    def create_batch(self, servers: List[ServerCreate], current_user: User) -> List[ServerResponse]:
        server_model_list = []
        for server_data in servers:
            server_data.user_id = current_user.id
            self._validate_server_data(server_data)
                
            if self.dao.check_hostname_exists(server_data.hostname):
                raise ValueError(f"Hostname '{server_data.hostname}'  already exists")
                
            if self.dao.check_ip_exists(server_data.ip_address):
                raise ValueError(f"IP address '{server_data.ip_address}' already exists")
            server_dict = server_data.dict()
            server_model_list.append(Server(**server_dict))
        try:
            created_servers = self.dao.create_batch(server_model_list)
            self.dao.db.commit()
            for server in created_servers:
                self.dao.db.refresh(server)
            return [self._convert_to_response(server) for server in created_servers]
        except IntegrityError as e:
            self.dao.db.rollback()
            if "hostname" in str(e.orig):
                raise ValueError("Hostname exsisted")
            elif "ip_address" in str(e.orig):
                raise ValueError("IP address exsisted")
            else:
                raise ValueError("Input is not valid")
        except Exception as e:
            self.dao.db.rollback()
            raise e
        

    def _convert_to_response(self, server: Server) -> ServerResponse:
        workload = self.workload_dao.get_by_id(server.workload_id)
        return ServerResponse(
            id=server.id,
            hostname=server.hostname,
            ip_address=server.ip_address,
            os_version=server.os_version,
            status=server.status,
            workload_name=workload.name,
            ssh_port=server.ssh_port,
          
            workload_id=server.workload_id,
            
            created_at=server.created_at,
            updated_at=server.updated_at,
            nameofmanager=server.user.username if server.user else None
        )

    def _validate_server_data(self, server_data: ServerCreate) -> None:
        if not server_data.hostname or not server_data.hostname.strip():
            raise ValueError("Hostname is not empty")
        
        if not server_data.ip_address or not server_data.ip_address.strip():
            raise ValueError("IP address is not empty")
       

       

        # Validate SSH port
        if server_data.ssh_port <= 0 or server_data.ssh_port > 65535:
            raise ValueError("SSH port must be between 1 and 65535")

    def _validate_update_data(self, server_data: ServerUpdate) -> None:
        if server_data.hostname is not None and not server_data.hostname.strip():
            raise ValueError("Hostname is not empty")

        if server_data.ip_address is not None and not server_data.ip_address.strip():
            raise ValueError("IP address is not empty")

        
        # Validate SSH port if present
        if server_data.ssh_port is not None:
            if server_data.ssh_port <= 0 or server_data.ssh_port > 65535:
                raise ValueError("SSH port must be between 1 and 65535")
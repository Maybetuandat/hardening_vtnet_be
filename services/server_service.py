from typing import List, Optional
from venv import create
from sqlalchemy.orm import Session
from dao.server_dao import ServerDAO
from models.server import Server
from schemas.server import (
    ServerCreate, 
    ServerUpdate, 
    ServerResponse, 
    ServerListResponse, 
    ServerSearchParams,
    ServerUploadItem
)
import math

from services.workload_service import WorkloadService


class ServerService:
    def __init__(self, db: Session):
        self.dao = ServerDAO(db)
        self.workload_service =WorkloadService(db)

    def get_all_servers(self, page: int = 1, page_size: int = 10) -> ServerListResponse:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100: 
            page_size = 100
            
        skip = (page - 1) * page_size
        servers, total = self.dao.get_all(skip=skip, limit=page_size)
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

    def get_server_by_id(self, server_id: int) -> Optional[ServerResponse]:
        if server_id <= 0:
            return None
            
        server = self.dao.get_by_id(server_id)
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
            limit=page_size
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

    def create_server(self, server_data: ServerCreate) -> ServerResponse:
        try:
            
            self._validate_server_data(server_data)
            
            
            if self.dao.check_hostname_exists(server_data.hostname):
                raise ValueError("Hostname đã tồn tại")
            
            
            if self.dao.check_ip_exists(server_data.ip_address):
                raise ValueError("IP address đã tồn tại")
            
            
            server_dict = server_data.dict()
            server_model = Server(**server_dict)
            
            
            created_server = self.dao.create(server_model)
            
            return self._convert_to_response(created_server)
            
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(f"Lỗi khi tạo server: {str(e)}")

    def update_server(self, server_id: int, server_data: ServerUpdate) -> Optional[ServerResponse]:
        try:
            if server_id <= 0:
                return None
                
            
            existing_server = self.dao.get_by_id(server_id)
            if not existing_server:
                return None
                
            
            if server_data.hostname or server_data.ip_address:
                self._validate_update_data(server_data)
            
            # kiem tra xem hostname co ton tai chua ? 
            if server_data.hostname and server_data.hostname != existing_server.hostname:
                if self.dao.check_hostname_exists(server_data.hostname, exclude_id=server_id):
                    raise ValueError("Hostname đã tồn tại")
            
            # kiem tra xem ip co ton tai chua 
            if server_data.ip_address and server_data.ip_address != existing_server.ip_address:
                if self.dao.check_ip_exists(server_data.ip_address, exclude_id=server_id):
                    raise ValueError("IP address đã tồn tại")
            
            
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

    def delete_server(self, server_id: int) -> bool:
        try:
            if server_id <= 0:
                return False
                
            
            existing_server = self.dao.get_by_id(server_id)
            if not existing_server:
                return False
            
            return self.dao.delete(server_id)
            
        except Exception as e:
            raise Exception(f"Lỗi khi xóa server: {str(e)}")

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

   

    def create_servers_from_upload_items(self, upload_items: List[ServerUploadItem]) -> List[ServerResponse]:
        """
        Tạo nhiều servers từ ServerUploadItem list
        Convert workload_name thành workload_id và tạo ServerCreate objects
        """
        created_servers = []
        errors = []
        
        for index, upload_item in enumerate(upload_items):
            try:
                # 1. Lấy workload_id từ workload_name
                workload_id = self.workload_service.get_workload_id_by_name(upload_item.workload_name)
                
                if not workload_id:
                    errors.append(f"Server {index + 1}: Workload '{upload_item.workload_name}' không tồn tại")
                    continue
                
                if self.dao.check_ip_exists(upload_item.ip_address):
                    errors.append(f"Server {index + 1}: IP address '{upload_item.ip_address}' đã tồn tại")
                    continue
                
                # 3. Tạo ServerCreate object
                server_create = ServerCreate(
                    ip_address=upload_item.ip_address,
                    hostname=upload_item.hostname or f"server-{upload_item.ip_address.replace('.', '-')}",
                    os_version=upload_item.os_version or "Unknown",
                    ssh_port=upload_item.ssh_port,
                    ssh_user=upload_item.ssh_user,
                    ssh_password=upload_item.ssh_password,
                    status=True,  # Mặc định active
                    workload_id=workload_id  # Set workload_id đã resolve
                )
                
                # 4. Tạo server
                created_server = self.create_server(server_create)
                created_servers.append(created_server)
                
            except Exception as e:
                errors.append(f"Server {index + 1}: {str(e)}")
                continue
        
        # Nếu có lỗi, raise exception với thông tin chi tiết
        if errors:
            error_message = "Một số server không thể tạo:\n" + "\n".join(errors)
            if not created_servers:  # Nếu không có server nào được tạo thành công
                raise ValueError(error_message)
            else:  # Nếu có một số thành công, một số thất bại
                # Log errors nhưng vẫn trả về kết quả thành công
                print(f"Warning: {error_message}")
        
        return created_servers







    def create_servers_batch(self, servers: List[ServerCreate]) -> List[ServerResponse]:
        created_servers = []
        for server_data in servers:
            try:
                self._validate_server_data(server_data)
                
                if self.dao.check_hostname_exists(server_data.hostname):
                    raise ValueError(f"Hostname '{server_data.hostname}' đã tồn tại")
                
                if self.dao.check_ip_exists(server_data.ip_address):
                    raise ValueError(f"IP address '{server_data.ip_address}' đã tồn tại")
                
                server_dict = server_data.dict()
                server_model = Server(**server_dict)
                
                created_server = self.dao.create(server_model)
                created_servers.append(self._convert_to_response(created_server))
            except ValueError as e:
                raise ValueError(str(e))
            except Exception as e:
                raise Exception(f"Lỗi khi tạo server: {str(e)}")
        
        return created_servers
    def _convert_to_response(self, server: Server) -> ServerResponse:
        return ServerResponse(
            id=server.id,
            hostname=server.hostname,
            ip_address=server.ip_address,
            os_version=server.os_version,
            status=server.status,
            ssh_port=server.ssh_port,
            ssh_user=server.ssh_user,
              workload_id=server.workload_id,
            ssh_password=getattr(server, 'ssh_password', None),
            created_at=server.created_at,
            updated_at=server.updated_at
        )

    def _validate_server_data(self, server_data: ServerCreate) -> None:
        if not server_data.hostname or not server_data.hostname.strip():
            raise ValueError("Hostname không được để trống")
            
        if not server_data.ip_address or not server_data.ip_address.strip():
            raise ValueError("IP address không được để trống")
            
        if not server_data.ssh_user or not server_data.ssh_user.strip():
            raise ValueError("SSH user không được để trống")
            
        if not server_data.ssh_password or not server_data.ssh_password.strip():
            raise ValueError("SSH password không được để trống")
            
        # Validate SSH port
        if server_data.ssh_port <= 0 or server_data.ssh_port > 65535:
            raise ValueError("SSH port phải trong khoảng 1-65535")

    def _validate_update_data(self, server_data: ServerUpdate) -> None:
        if server_data.hostname is not None and not server_data.hostname.strip():
            raise ValueError("Hostname không được để trống")
            
        if server_data.ip_address is not None and not server_data.ip_address.strip():
            raise ValueError("IP address không được để trống")
            
        if server_data.ssh_user is not None and not server_data.ssh_user.strip():
            raise ValueError("SSH user không được để trống")
            
        # Validate SSH port nếu có
        if server_data.ssh_port is not None:
            if server_data.ssh_port <= 0 or server_data.ssh_port > 65535:
                raise ValueError("SSH port phải trong khoảng 1-65535")
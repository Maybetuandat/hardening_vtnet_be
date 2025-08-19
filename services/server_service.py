from typing import List, Optional
from sqlalchemy.orm import Session
from dao.server_dao import ServerDAO
from models.server import Server
from schemas.server import (
    ServerCreate, 
    ServerUpdate, 
    ServerResponse, 
    ServerListResponse, 
    ServerSearchParams
)
import math


class ServerService:
    def __init__(self, db: Session):
        self.dao = ServerDAO(db)

    def get_all_servers(self, page: int = 1, page_size: int = 10) -> ServerListResponse:
        """Lấy danh sách tất cả server với phân trang - deprecated, sử dụng search_servers thay thế"""
        search_params = ServerSearchParams(page=page, size=page_size)
        return self.search_servers(search_params)

    def get_server_by_id(self, server_id: int) -> Optional[ServerResponse]:
        """Lấy server theo ID"""
        server = self.dao.get_by_id(server_id)
        if server:
            return ServerResponse(
                id=server.id,
                hostname=server.hostname,
                ip_address=server.ip_address,
                os_version=server.os_version,
                status=server.status,
                ssh_port=server.ssh_port,
                ssh_user=server.ssh_user,
                created_at=server.created_at,
                updated_at=server.updated_at
            )
        return None

    def search_servers(self, search_params: ServerSearchParams) -> ServerListResponse:
        """Tìm kiếm server với các bộ lọc"""
        skip = (search_params.page - 1) * search_params.size
        
        servers, total = self.dao.search_servers(
            keyword=search_params.keyword,
            workload_id=search_params.workload_id,
            status=search_params.status,
            skip=skip,
            limit=search_params.size
        )
        
        total_pages = math.ceil(total / search_params.size) if total > 0 else 0
        
        server_responses = []
        for server in servers:
            server_responses.append(ServerResponse(
                id=server.id,
                hostname=server.hostname,
                ip_address=server.ip_address,
                os_version=server.os_version,
                status=server.status,
                ssh_port=server.ssh_port,
                ssh_user=server.ssh_user,
                created_at=server.created_at,
                updated_at=server.updated_at
            ))
        
        return ServerListResponse(
            servers=server_responses,
            total_servers=total,
            page=search_params.page,
            page_size=search_params.size,
            total_pages=total_pages
        )
    def create_server(self, server_data: ServerCreate) -> ServerResponse:
        """Tạo server mới"""
        try:
            server = self.dao.create(server_data)
            return ServerResponse(
                id=server.id,
                hostname=server.hostname,
                ip_address=server.ip_address,
                os_version=server.os_version,
                status=server.status,
                ssh_port=server.ssh_port,
                ssh_user=server.ssh_user,
                created_at=server.created_at,
                updated_at=server.updated_at
            )
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(f"Lỗi khi tạo server: {str(e)}")

    def update_server(self, server_id: int, server_data: ServerUpdate) -> Optional[ServerResponse]:
        """Cập nhật server"""
        try:
            server = self.dao.update(server_id, server_data)
            if server:
                return ServerResponse(
                    id=server.id,
                    hostname=server.hostname,
                    ip_address=server.ip_address,
                    os_version=server.os_version,
                    status=server.status,
                    ssh_port=server.ssh_port,
                    ssh_user=server.ssh_user,
                    created_at=server.created_at,
                    updated_at=server.updated_at
                )
            return None
        except ValueError as e:
            raise ValueError(str(e))
        except Exception as e:
            raise Exception(f"Lỗi khi cập nhật server: {str(e)}")

    def delete_server(self, server_id: int) -> bool:
        """Xóa server (hard delete vì không có is_active)"""
        try:
            return self.dao.delete(server_id)
        except Exception as e:
            raise Exception(f"Lỗi khi xóa server: {str(e)}")
    def test_server_connection(self, server_id: int) -> dict:
        """Test kết nối đến server (placeholder for future implementation)"""
        server = self.dao.get_by_id(server_id)
        if not server:
            raise ValueError("Server không tồn tại")
        
        # TODO: Implement actual connection test using SSH
        # For now, return a mock response
        return {
            "server_id": server_id,
            "hostname": server.hostname,
            "ip_address": server.ip_address,
            "ssh_port": server.ssh_port,
            "status": "success",
            "message": "Kết nối thành công",
            "response_time": 100
        }
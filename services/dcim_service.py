import logging
from typing import Optional, List

from clients.dcim_client import dcim_client
from schemas.dcim_schema import (
    ServerListRequest,
    ServerDetailRequest,
    ServerListResponse,
    ServerDetailResponse,
    CacheClearRequest,
    CacheClearResponse,
    ServerData
)
from config.redis_config import redis_settings

logger = logging.getLogger(__name__)


class DCIMService:
    """
    DCIM Service - Business Logic Layer
    Trách nhiệm:
    - Validate input data
    - Transform data giữa API response và application models
    - Xử lý business rules
    - Format output data
    """
    
    def __init__(self):
        self.client = dcim_client
    
    def get_servers(self, request: ServerListRequest) -> Optional[ServerListResponse]:
        """
        Lấy danh sách servers từ DCIM
        
        Args:
            request: ServerListRequest với page, page_size, use_cache
            
        Returns:
            ServerListResponse hoặc None nếu lỗi
        """
        try:
            # Validate input
            if request.page < 1:
                logger.warning(f"Invalid page number: {request.page}")
                return None
            
            if request.page_size < 1 or request.page_size > 100:
                logger.warning(f"Invalid page_size: {request.page_size}")
                return None
            
            # Gọi client để lấy dữ liệu
            endpoint = "/api/instances/"
            params = {
                "page": request.page,
                "page_size": request.page_size
            }
            
            raw_data = self.client.get(
                endpoint=endpoint,
                params=params,
                use_cache=request.use_cache,
                cache_ttl=redis_settings.CACHE_TTL_DCIM_SERVERS
            )
            
            if raw_data is None:
                logger.error("Failed to fetch servers from DCIM")
                return None
            
            # Transform data sang response model
            server_list = [ServerData(**item) for item in raw_data.get("data", [])]
            
            response = ServerListResponse(
                cached=request.use_cache,
                data=server_list,
                page=raw_data.get("page", request.page),
                page_size=raw_data.get("page_size", request.page_size),
                total=raw_data.get("total", 0),
                total_pages=raw_data.get("total_pages", 0),
                has_next=raw_data.get("has_next", False),
                has_prev=raw_data.get("has_prev", False)
            )
            
            logger.info(f"✅ Retrieved {len(server_list)} servers (page {request.page})")
            return response
            
        except Exception as e:
            logger.error(f"Error in get_servers service: {e}")
            return None
    
    def get_server_by_id(self, request: ServerDetailRequest) -> Optional[ServerDetailResponse]:
        """
        Lấy chi tiết 1 server từ DCIM
        
        Args:
            request: ServerDetailRequest với server_id, use_cache
            
        Returns:
            ServerDetailResponse hoặc None nếu không tìm thấy
        """
        try:
            # Validate input
            if request.server_id < 1:
                logger.warning(f"Invalid server_id: {request.server_id}")
                return None
            
            # Gọi client
            endpoint = f"/api/instances/{request.server_id}/"
            
            raw_data = self.client.get(
                endpoint=endpoint,
                use_cache=request.use_cache,
                cache_ttl=redis_settings.CACHE_TTL_DCIM_SERVER_DETAIL
            )
            
            if raw_data is None:
                logger.warning(f"Server {request.server_id} not found")
                return None
            
            # Transform data
            server_data = ServerData(**raw_data)
            
            response = ServerDetailResponse(
                cached=request.use_cache,
                data=server_data
            )
            
            logger.info(f"✅ Retrieved server {request.server_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error in get_server_by_id service: {e}")
            return None
    
    def clear_cache(self, request: CacheClearRequest) -> CacheClearResponse:
        """
        Xóa cache của DCIM
        
        Args:
            request: CacheClearRequest với server_id (optional)
            
        Returns:
            CacheClearResponse với thông tin số keys đã xóa
        """
        try:
            if request.server_id:
                # Xóa cache của 1 server cụ thể
                pattern = f"dcim:api:instances:{request.server_id}*"
                deleted = self.client.clear_cache(pattern)
                message = f"Cleared cache for server {request.server_id}"
            else:
                # Xóa toàn bộ cache DCIM
                pattern = "dcim:*"
                deleted = self.client.clear_cache(pattern)
                message = "Cleared all DCIM cache"
            
            response = CacheClearResponse(
                message=message,
                deleted_keys=deleted
            )
            
            logger.info(f"✅ {message} ({deleted} keys)")
            return response
            
        except Exception as e:
            logger.error(f"Error in clear_cache service: {e}")
            return CacheClearResponse(
                success=False,
                message=f"Error: {str(e)}",
                deleted_keys=0
            )
    
    def search_servers(
        self,
        keyword: Optional[str] = None,
        use_cache: bool = True
    ) -> Optional[ServerListResponse]:
        """
        Tìm kiếm servers theo keyword
        
        Args:
            keyword: Từ khóa tìm kiếm (IP, hostname, etc.)
            use_cache: Có sử dụng cache không
            
        Returns:
            ServerListResponse hoặc None nếu lỗi
        """
        try:
            # Business logic: nếu keyword rỗng thì lấy tất cả
            if not keyword or not keyword.strip():
                request = ServerListRequest(page=1, page_size=100, use_cache=use_cache)
                return self.get_servers(request)
            
            # TODO: Implement search logic khi DCIM API có hỗ trợ search
            # Hiện tại chỉ lấy tất cả và filter ở application layer
            
            endpoint = "/api/instances/"
            params = {
                "page": 1,
                "page_size": 100,
                "search": keyword.strip()  # Giả sử API support param này
            }
            
            raw_data = self.client.get(
                endpoint=endpoint,
                params=params,
                use_cache=use_cache
            )
            
            if raw_data is None:
                return None
            
            # Transform data
            server_list = [ServerData(**item) for item in raw_data.get("data", [])]
            
            # Filter ở application layer nếu cần
            filtered_servers = [
                server for server in server_list
                if keyword.lower() in server.name.lower()
            ]
            
            response = ServerListResponse(
                cached=use_cache,
                data=filtered_servers,
                page=1,
                page_size=len(filtered_servers),
                total=len(filtered_servers),
                total_pages=1,
                has_next=False,
                has_prev=False
            )
            
            logger.info(f"✅ Search results: {len(filtered_servers)} servers match '{keyword}'")
            return response
            
        except Exception as e:
            logger.error(f"Error in search_servers service: {e}")
            return None


# Singleton instance
dcim_service = DCIMService()
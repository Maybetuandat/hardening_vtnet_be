import logging
from typing import Optional

from client.dcim_client import dcim_client
from config.setting_redis import get_redis_settings
from schemas.dcim_cache import CacheClearRequest, CacheClearResponse
from schemas.instance import InstanceListRequest, InstanceListResponseFromDcim

redis_settings = get_redis_settings()

logger = logging.getLogger(__name__)


class DCIMService:
    """
    DCIM Service - Business Logic Layer
    Trách nhiệm:
    - Validate input data
    - Transform data giữa DCIM API response và application models
    - Xử lý business rules
    """
    
    def __init__(self):
        self.client = dcim_client
    
    def get_instances(self, request: InstanceListRequest) -> Optional[InstanceListResponseFromDcim]:
        """
        Lấy danh sách instances từ DCIM với pagination
        
        Args:
            request: InstanceListRequest với page, page_size, use_cache
            
        Returns:
            InstanceListResponseFromDcim hoặc None nếu lỗi
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
            endpoint = "/api/v1/instances/"
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
                logger.error("Failed to fetch instances from DCIM")
                return None
            
            # Log raw data để debug
            logger.info(f"Raw data keys: {raw_data.keys()}")
            
            # ✅ Transform: Map field names từ DCIM response sang schema
            transformed_data = {
                "instances": raw_data.get("instances", []),  # 'data' -> 'instances'
                "total_instances": raw_data.get("total", 0),  # 'total' -> 'total_instances'
                "page": raw_data.get("page", request.page),
                "page_size": raw_data.get("page_size", request.page_size),
                "total": raw_data.get("total", 0),
                "total_pages": raw_data.get("total_pages", 0)
            }
            
            logger.info(f"Transformed data keys: {transformed_data.keys()}")
            logger.info(f"Number of instances: {len(transformed_data['instances'])}")
            
            # Parse transformed data thành InstanceListResponseFromDcim
            response = InstanceListResponseFromDcim(**transformed_data)
            
            logger.info(f"✅ Retrieved {len(response.instances)} instances (page {response.page}/{response.total_pages})")
            return response
            
        except Exception as e:
            logger.error(f"Error in get_instances service: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def clear_cache(self, request: CacheClearRequest) -> CacheClearResponse:
        """
        Xóa cache của DCIM
        
        Args:
            request: CacheClearRequest với instance_id (optional)
            
        Returns:
            CacheClearResponse với thông tin số keys đã xóa
        """
        try:
            if request.instance_id:
                # Xóa cache của 1 instance cụ thể
                pattern = f"dcim:api:instances:{request.instance_id}*"
                deleted = self.client.clear_cache(pattern)
                message = f"Cleared cache for instance {request.instance_id}"
            else:
                # Xóa toàn bộ cache DCIM
                pattern = "dcim:*"
                deleted = self.client.clear_cache(pattern)
                message = "Cleared all DCIM cache"
            
            response = CacheClearResponse(
                success=True,
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
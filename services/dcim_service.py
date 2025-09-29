import logging
from typing import Any, Dict, Optional

from client.dcim_client import dcim_client
from config.setting_redis import get_redis_settings
from schemas.instance import InstanceListRequest, InstanceListResponseFromDcim

redis_settings = get_redis_settings()
logger = logging.getLogger(__name__)


class DCIMService:
   
    def __init__(self):
        self.client = dcim_client
    
    def cache_all_instances_incrementally(
        self,
        page_size: int = 100,
        cache_ttl: Optional[int] = None
    ) -> Dict[str, Any]:
       
        try:
       
            logger.info("🗑️ Clearing old cache...")
            self.client.clear_cache()
            
            page = 1
            total_cached = 0
            total_from_api = 0
            
            
            
            while True:
            
            
                
                endpoint = "/api/v1/instances/"
                params = {
                    "page": page,
                    "page_size": page_size
                }
                
                raw_data = self.client.get_single_page(
                    endpoint=endpoint,
                    params=params
                )
                
                if raw_data is None:
                    logger.error(f"❌ Failed to fetch page {page}, stopping...")
                    break
                
                # Lấy thông tin từ response
                instances = raw_data.get("instances", [])
                total_from_api = raw_data.get("total", 0)
                current_page = raw_data.get("page", page)
                total_pages = raw_data.get("total_pages", 0)
                
                logger.info(
                    f"✅ Page {current_page}/{total_pages}: "
                    f"fetched {len(instances)} instances"
                )
                
                # Kiểm tra xem có data không
                if not instances:
                    logger.info("ℹ️ No more instances, stopping...")
                    break
                
                # Append instances vào cache ngay lập tức
                success = self.client.append_to_cache(
                    new_instances=instances,
                    cache_ttl=cache_ttl
                )
                
                if not success:
                    logger.error(f"❌ Failed to cache page {page}")
                    # Vẫn tiếp tục fetch pages tiếp theo
                
                total_cached += len(instances)
                
                logger.info(
                    f"💾 Cached progress: {total_cached}/{total_from_api} instances"
                )
                
                # Kiểm tra xem đã hết chưa
                if current_page >= total_pages:
                    logger.info("✅ Reached last page, stopping...")
                    break
                
                # Tăng page number
                page += 1
            
            # Bước cuối: Cập nhật total chính xác
            if total_cached > 0:
                self.client.update_cache_total(
                    total=total_from_api,
                    cache_ttl=cache_ttl
                )
            
            logger.info(
                f"🎉 Incremental cache completed: "
                f"{total_cached} instances cached"
            )
            
            return {
                "success": True,
                "total_cached": total_cached,
                "total_from_api": total_from_api,
                "pages_fetched": page,
                "cache_key": self.client.cache_key
            }
            
        except Exception as e:
            logger.error(f"❌ Error in incremental cache: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                "success": False,
                "error": str(e),
                "total_cached": total_cached if 'total_cached' in locals() else 0
            }
    
    def get_cached_instances(self) -> Optional[Dict[str, Any]]:
        """
        Lấy toàn bộ cached instances
        
        Returns:
            Cached data hoặc None nếu không có cache
        """
        try:
            cached_data = self.client.get_cached_data()
            
            if cached_data is None:
                logger.info("No cached instances found")
                return None
            
            logger.info(
                f"✅ Retrieved {cached_data.get('total_records', 0)} "
                f"instances from cache"
            )
            
            return cached_data
            
        except Exception as e:
            logger.error(f"Error getting cached instances: {e}")
            return None
    
    
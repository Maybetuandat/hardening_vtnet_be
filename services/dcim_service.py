import logging
from typing import Any, Dict, List, Optional

from client.dcim_client import dcim_client
from config.setting_redis import get_redis_settings

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
            
            endpoint = "/api/v1/instances/"
            params = {
                "page": page,
                "page_size": page_size
            }
            
            while True:
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
                params["page"] = page
            
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
    
    def get_cached_instances(self) -> Optional[List[Dict]]:
        """Lấy instances từ cache"""
        try:
            cached_data = self.client.get_cached_data()
            
            if cached_data is None:
                print("❌ No cached instances found")
                return None
            
           
            
            
            
            return cached_data
            
        except Exception as e:
            logger.error(f"❌ Error getting cached instances: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def sync_data_from_dcim(self):
        """Đồng bộ dữ liệu từ DCIM vào cache"""
        try:
            print("🔄 Starting DCIM sync...")
            
            result = self.cache_all_instances_incrementally(
                page_size=100,
                cache_ttl=redis_settings.CACHE_TTL_DCIM_INSTANCES
            )
            
            if not result.get("success", False):
                logger.error("❌ Failed to sync data from DCIM")
                return None
            
            print(f"✅ Sync completed: {result}")
            
            # Logic thực hiện so sánh với cache của backend server
            cached_data = self.get_cached_instances()
            
            if cached_data is None:
                logger.error("❌ Failed to retrieve cached data after sync")
                return None
            
            print(f"✅ Processing {len(cached_data)} instances...")
            
            
            i = 0
            for instance in cached_data:
                # Xử lý từng instance
                i += 1
                print(i, " ")

            return result
            
        except Exception as e:
            logger.error(f"❌ Error syncing data from DCIM: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
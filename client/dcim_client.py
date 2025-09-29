import logging
from typing import Optional, Dict, Any, List
import requests

from config.setting_dcim import get_dcim_settings
from config.setting_redis import get_redis_settings
from utils.redis_client import CacheManager

logger = logging.getLogger(__name__)
dcim_settings = get_dcim_settings()
redis_settings = get_redis_settings()

class DCIMClient:
   
    def __init__(self):
        self.base_url = dcim_settings.DCIM_BASE_URL
        self.timeout = dcim_settings.DCIM_TIMEOUT
        self.cache = CacheManager()
        self.cache_key = redis_settings.CACHE_DCIM_KEY
        
    
    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict]]:
        
        try:
            return self.cache.get(cache_key)
            
        except Exception as e:
            logger.error(f"Error reading cache: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _set_to_cache(self, cache_key: str, data: Any, ttl: int) -> bool:
        
        try:
            if self.cache.set(cache_key, data, ttl):
                logger.info(f"💾 Cached: {cache_key} (TTL: {ttl}s, {len(data)} items)")
                return True
            return False
        except Exception as e:
            logger.error(f"Error setting cache: {e}")
            return False
    
    def _make_http_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """Thực hiện HTTP request"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            logger.info(f"🌐 HTTP Request: {method} {url}")
            if params:
                logger.info(f"   Params: {params}")
            
            response = requests.request(
                method=method,
                url=url,
                params=params,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"✅ HTTP Success: {response.status_code}")
            return data
            
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Request timeout after {self.timeout}s")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"🔌 Connection error to {self.base_url}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ HTTP Error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return None
    
    def get_single_page(
        self,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        
        return self._make_http_request("GET", endpoint, params)
    
    def append_to_cache(
        self,
        new_instances: List[Dict],
        cache_ttl: Optional[int] = None
    ) -> bool:
        """Thêm instances mới vào cache"""
        try:
            # Lấy cached data hiện tại
            cached_data = self._get_from_cache(self.cache_key)
            
            if cached_data is None:
                all_instances = new_instances
                logger.info(f"📝 Creating new cache with {len(new_instances)} instances")
            else: 
                all_instances = cached_data + new_instances
                logger.info(f"➕ Appending {len(new_instances)} instances to existing {len(cached_data)}")
            
            # Lưu lại vào cache
            ttl = cache_ttl or redis_settings.CACHE_TTL_DCIM_INSTANCES
            success = self._set_to_cache(self.cache_key, all_instances, ttl)
            
            if success:
                logger.info(
                    f"✅ Cache updated: {len(all_instances)} total instances "
                    f"in key: {self.cache_key}"
                )
            else:
                logger.error("❌ Failed to update cache")
            
            return success
            
        except Exception as e:
            logger.error(f"Error appending to cache: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def get_cached_data(self) -> Optional[List[Dict]]:
       
        return self._get_from_cache(self.cache_key)
    
    def clear_cache(self, pattern: str = None) -> int:
        """Xóa cache"""
        try:
            if pattern is None:
                # Mặc định: Xóa CHỈ cache key instances
                if self.cache.delete(self.cache_key):
                    logger.info(f"🗑️ Cleared instances cache: {self.cache_key}")
                    return 1
                return 0
            else:
                # Xóa theo pattern (cẩn thận!)
                deleted = self.cache.delete_pattern(pattern)
                logger.info(f"🗑️ Cleared cache pattern: {pattern} ({deleted} keys)")
                return deleted
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0


# Singleton instance
dcim_client = DCIMClient()
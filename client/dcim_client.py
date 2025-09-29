import logging
from typing import Optional, Dict, Any
import requests

from config.dcim_config import  get_dcim_settings

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
        self.key="dcim-cache-all-instances"
        logger.info(f"🔧 DCIM Client initialized: {self.base_url}")
    
   
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Lấy dữ liệu từ cache"""
        try:
            data = self.cache.get(cache_key)
            if data is not None:
                logger.info(f"🎯 Cache HIT: {cache_key}")
                return data
            
            logger.info(f"❌ Cache MISS: {cache_key}")
            return None
        except Exception as e:
            logger.error(f"Error reading cache: {e}")
            return None
    
    def _set_to_cache(self, cache_key: str, data: Any, ttl: int) -> bool:
        """Lưu dữ liệu vào cache"""
        try:
            if self.cache.set(cache_key, data, ttl):
                logger.info(f"💾 Cached: {cache_key} (TTL: {ttl}s)")
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
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        
        # Tạo cache key
     
        
        # Thử lấy từ cache trước
        if use_cache:
            cached_data = self._get_from_cache(self.key)
            if cached_data is not None:
                return cached_data
        
        # Cache miss -> gọi API
        data = self._make_http_request("GET", endpoint, params)
        
        if data is None:
            return None
        
        # Lưu vào cache
        if use_cache:
            ttl = cache_ttl or redis_settings.CACHE_TTL_DCIM_INSTANCES
            self._set_to_cache(self.key, data, ttl)
        
        return data
    
    def clear_cache(self, pattern: str) -> int:
        """
        Xóa cache theo pattern
        
        Args:
            pattern: Redis key pattern (vd: dcim:*, dcim:api:instances:3*)
            
        Returns:
            Số lượng keys đã xóa
        """
        try:
            deleted = self.cache.delete_pattern(pattern)
            logger.info(f"🗑️ Cleared cache: {pattern} ({deleted} keys)")
            return deleted
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0


# Singleton instance
dcim_client = DCIMClient()
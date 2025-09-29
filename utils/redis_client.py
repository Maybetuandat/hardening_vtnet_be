import redis
from typing import Optional, Any
import json
import logging
from config.redis_config import redis_settings

logger = logging.getLogger(__name__)


class RedisClient:
  
    _instance: Optional[redis.Redis] = None
    
    @classmethod
    def get_instance(cls) -> Optional[redis.Redis]:
        """
        Lấy Redis connection instance (Singleton)
        
        Returns:
            Redis instance hoặc None nếu không kết nối được
        """
        if cls._instance is None:
            try:
                cls._instance = redis.Redis(
                    host=redis_settings.REDIS_HOST,
                    port=redis_settings.REDIS_PORT,
                    db=redis_settings.REDIS_DB,
                    password=redis_settings.REDIS_PASSWORD,
                    decode_responses=redis_settings.REDIS_DECODE_RESPONSES,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
                
                # Test connection
                cls._instance.ping()
                logger.info(
                    f"✅ Redis connected: {redis_settings.REDIS_HOST}:{redis_settings.REDIS_PORT}"
                )
                
            except redis.exceptions.ConnectionError as e:
                logger.error(f"❌ Redis connection failed: {e}")
                cls._instance = None
            except Exception as e:
                logger.error(f"❌ Redis unexpected error: {e}")
                cls._instance = None
        
        return cls._instance
    
    @classmethod
    def close(cls):
        """Đóng Redis connection"""
        if cls._instance:
            cls._instance.close()
            cls._instance = None
            logger.info("Redis connection closed")


class CacheManager:
    """
    Cache Manager - Helper class để thao tác với Redis cache
    
    Các method chính:
    - get(key): Lấy dữ liệu từ cache
    - set(key, value, ttl): Lưu dữ liệu vào cache
    - delete(key): Xóa 1 key
    - delete_pattern(pattern): Xóa nhiều keys theo pattern
    - exists(key): Kiểm tra key có tồn tại không
    """
    
    @staticmethod
    def get(key: str) -> Optional[Any]:
        """
        Lấy dữ liệu từ cache
        
        Args:
            key: Cache key
            
        Returns:
            Data (đã parse JSON) hoặc None nếu không có
        """
        try:
            redis_client = RedisClient.get_instance()
            if redis_client is None:
                logger.warning("Redis not available, skipping cache get")
                return None
            
            data = redis_client.get(key)
            if data:
                return json.loads(data)
            
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from cache key '{key}': {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting cache '{key}': {e}")
            return None
    
    @staticmethod
    def set(key: str, value: Any, ttl: int) -> bool:
        """
        Lưu dữ liệu vào cache với TTL
        
        Args:
            key: Cache key
            value: Data cần lưu (sẽ được JSON serialize)
            ttl: Time to live (seconds)
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            redis_client = RedisClient.get_instance()
            if redis_client is None:
                logger.warning("Redis not available, skipping cache set")
                return False
            
            # Serialize data thành JSON
            json_data = json.dumps(value, default=str, ensure_ascii=False)
            
            # Lưu vào Redis với TTL
            redis_client.setex(key, ttl, json_data)
            return True
            
        except TypeError as e:
            logger.error(f"Error serializing data for cache key '{key}': {e}")
            return False
        except Exception as e:
            logger.error(f"Error setting cache '{key}': {e}")
            return False
    
    @staticmethod
    def delete(key: str) -> bool:
        """
        Xóa 1 cache key
        
        Args:
            key: Cache key cần xóa
            
        Returns:
            True nếu thành công, False nếu thất bại
        """
        try:
            redis_client = RedisClient.get_instance()
            if redis_client is None:
                logger.warning("Redis not available, skipping cache delete")
                return False
            
            redis_client.delete(key)
            logger.info(f"🗑️ Deleted cache: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting cache '{key}': {e}")
            return False
    
    @staticmethod
    def delete_pattern(pattern: str) -> int:
        """
        Xóa nhiều cache keys theo pattern
        
        Args:
            pattern: Redis key pattern (vd: dcim:*, user:123:*)
            
        Returns:
            Số lượng keys đã xóa
        """
        try:
            redis_client = RedisClient.get_instance()
            if redis_client is None:
                logger.warning("Redis not available, skipping cache delete pattern")
                return 0
            
            # Tìm tất cả keys match với pattern
            keys = redis_client.keys(pattern)
            
            if keys:
                # Xóa tất cả keys tìm được
                deleted = redis_client.delete(*keys)
                logger.info(f"🗑️ Deleted {deleted} cache keys matching: {pattern}")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Error deleting cache pattern '{pattern}': {e}")
            return 0
    
    @staticmethod
    def exists(key: str) -> bool:
        """
        Kiểm tra cache key có tồn tại không
        
        Args:
            key: Cache key
            
        Returns:
            True nếu tồn tại, False nếu không
        """
        try:
            redis_client = RedisClient.get_instance()
            if redis_client is None:
                return False
            
            return redis_client.exists(key) > 0
            
        except Exception as e:
            logger.error(f"Error checking cache existence '{key}': {e}")
            return False
    
    @staticmethod
    def get_ttl(key: str) -> int:
        """
        Lấy thời gian còn lại của cache key (TTL)
        
        Args:
            key: Cache key
            
        Returns:
            TTL in seconds, -1 nếu key tồn tại nhưng không có TTL, -2 nếu key không tồn tại
        """
        try:
            redis_client = RedisClient.get_instance()
            if redis_client is None:
                return -2
            
            return redis_client.ttl(key)
            
        except Exception as e:
            logger.error(f"Error getting TTL for key '{key}': {e}")
            return -2
    
    @staticmethod
    def clear_all() -> bool:
        """
        Xóa toàn bộ cache trong DB hiện tại
        ⚠️ Sử dụng cẩn thận! Sẽ xóa TẤT CẢ keys
        
        Returns:
            True nếu thành công
        """
        try:
            redis_client = RedisClient.get_instance()
            if redis_client is None:
                logger.warning("Redis not available, skipping clear all")
                return False
            
            redis_client.flushdb()
            logger.warning("🗑️ CLEARED ALL CACHE in current DB")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing all cache: {e}")
            return False
    
    @staticmethod
    def get_all_keys(pattern: str = "*") -> list:
        """
        Lấy danh sách tất cả cache keys theo pattern
        
        Args:
            pattern: Redis key pattern (default: "*" = all keys)
            
        Returns:
            List of keys
        """
        try:
            redis_client = RedisClient.get_instance()
            if redis_client is None:
                return []
            
            keys = redis_client.keys(pattern)
            return [key.decode() if isinstance(key, bytes) else key for key in keys]
            
        except Exception as e:
            logger.error(f"Error getting all keys with pattern '{pattern}': {e}")
            return []
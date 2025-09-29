# services/backend_cache_service.py

import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import logging

from config.setting_redis import get_redis_settings

from dao.instance_dao import InstanceDAO
from models.instance import Instance
from utils.redis_client import CacheManager, RedisClient

logger = logging.getLogger(__name__)
redis_settings = get_redis_settings()


class BackendCacheService:
    """
    Service để cache dữ liệu Instance từ Backend Database vào Redis
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.redis_client = RedisClient.get_instance()  # Lấy Redis instance đúng cách
        self.cache_manager = CacheManager()  # Hoặc dùng CacheManager
        self.instance_dao = InstanceDAO(db)
    
    def get_instances_from_db(self) -> Optional[List[Dict[str, Any]]]:
        """
        Lấy tất cả instances từ database
        
        Returns:
            List of instances dict hoặc None nếu có lỗi
        """
        try:
            print("🔄 Fetching instances from database...")
            
            # Lấy tất cả instances từ DAO
            instances = self.instance_dao.get_all_instances()
            
            if not instances:
                print("⚠️ No instances found in database")
                return []
            
            # Convert SQLAlchemy objects to dict
            instances_list = []
            for instance in instances:
                instance_dict = {
                    "id": instance.id,
                    "name": instance.name,
                    "os_id": instance.os_id,
                    "workload_id": instance.workload_id,
                    "instance_role": instance.instance_role,
                    "user_id": instance.user_id,
                    "status": instance.status,
                    "ssh_port": instance.ssh_port,
                    "created_at": instance.created_at.isoformat() if instance.created_at else None,
                    "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
                }
                instances_list.append(instance_dict)
            
            print(f"✅ Fetched {len(instances_list)} instances from database")
            return instances_list
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch instances from database: {str(e)}")
            return None
    
    def cache_instances_to_redis(
        self, 
        instances: Optional[List[Dict[str, Any]]] = None,
        cache_key: Optional[str] = None,
        cache_ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Cache instances từ database vào Redis
        
        Args:
            instances: List instances cần cache (nếu None sẽ lấy từ DB)
            cache_key: Redis key để cache
            cache_ttl: Time to live cho cache (seconds)
            
        Returns:
            Dict với thông tin cache result
        """
        try:
            # Nếu không truyền instances, lấy từ database
            if instances is None:
                instances = self.get_instances_from_db()
                
            if instances is None:
                return {
                    "success": False,
                    "error": "Failed to fetch instances from database"
                }
            
            # Set default cache key và TTL
            if cache_key is None:
                cache_key = redis_settings.CACHE_BACKEND_KEY
            
            if cache_ttl is None:
                cache_ttl = redis_settings.CACHE_TTL_BACKEND_INSTANCES
            
            # Cache vào Redis
            print(f"🔄 Caching {len(instances)} instances to Redis...")
            print(f"   Key: {cache_key}")
            print(f"   TTL: {cache_ttl}s")
            
            # Kiểm tra Redis client có available không
            if self.redis_client is None:
                logger.error("❌ Redis client is not available")
                return {
                    "success": False,
                    "error": "Redis client is not available"
                }
            
            # CÁCH 1: Dùng CacheManager (Recommended)
            success = self.cache_manager.set(cache_key, instances, cache_ttl)
            
            if not success:
                return {
                    "success": False,
                    "error": "Failed to set cache using CacheManager"
                }
            
            # CÁCH 2: Dùng redis_client trực tiếp
            # self.redis_client.setex(
            #     cache_key,
            #     cache_ttl,
            #     json.dumps(instances, default=str)
            # )
            
            print(f"✅ Successfully cached {len(instances)} instances to Redis")
            
            return {
                "success": True,
                "cached_count": len(instances),
                "cache_key": cache_key,
                "ttl": cache_ttl
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to cache instances to Redis: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_cached_instances(self, cache_key: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
      
        try:
            if cache_key is None:
                cache_key = redis_settings.CACHE_BACKEND_KEY
            
            print(f"🔄 Retrieving instances from Redis cache: {cache_key}")
            
          
            instances = self.cache_manager.get(cache_key)
            
            
            if instances:
                print(f"✅ Retrieved {len(instances)} instances from Redis cache")
                return instances
            else:
                print("⚠️ No cached data found in Redis")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to get cached instances: {str(e)}")
            return None
    
    def refresh_cache(
        self, 
        cache_key: Optional[str] = None, 
        cache_ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Refresh cache: Lấy data mới từ DB và cache lại
        
        Returns:
            Dict với kết quả refresh
        """
        print("🔄 Refreshing backend instances cache...")
        return self.cache_instances_to_redis(
            cache_key=cache_key,
            cache_ttl=cache_ttl
        )
    
    def clear_cache(self, cache_key: Optional[str] = None) -> bool:
        """
        Xóa cache trong Redis
        
        Args:
            cache_key: Redis key cần xóa
            
        Returns:
            True nếu xóa thành công
        """
        try:
            if cache_key is None:
                cache_key = redis_settings.CACHE_BACKEND_KEY
            
            # CÁCH 1: Dùng CacheManager (Recommended)
            return self.cache_manager.delete(cache_key)
            
            # CÁCH 2: Dùng redis_client trực tiếp
            # if self.redis_client:
            #     self.redis_client.delete(cache_key)
            #     print(f"✅ Cleared cache: {cache_key}")
            #     return True
            # return False
            
        except Exception as e:
            logger.error(f"❌ Failed to clear cache: {str(e)}")
            return False
    
    def get_cache_info(self, cache_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Lấy thông tin về cache
        
        Args:
            cache_key: Redis key
            
        Returns:
            Dict với thông tin cache (exists, ttl, count)
        """
        try:
            if cache_key is None:
                cache_key = redis_settings.CACHE_BACKEND_KEY
            
            exists = self.cache_manager.exists(cache_key)
            ttl = self.cache_manager.get_ttl(cache_key) if exists else 0
            
            cached_data = self.cache_manager.get(cache_key) if exists else None
            count = len(cached_data) if cached_data else 0
            
            return {
                "cache_key": cache_key,
                "exists": exists,
                "ttl": ttl,
                "count": count
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get cache info: {str(e)}")
            return {
                "cache_key": cache_key,
                "exists": False,
                "ttl": 0,
                "count": 0,
                "error": str(e)
            }
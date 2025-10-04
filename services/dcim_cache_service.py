"""
File 2: dcim_cache_service.py
Service for caching DCIM data with pagination support
"""
import logging
from typing import Any, Dict, List, Optional

from models.user import User

logger = logging.getLogger(__name__)


class DCIMCacheService:
    """Service for caching DCIM data"""

    def __init__(self, dcim_client):
        self.client = dcim_client

    def cache_all_instances_incrementally(
        self,
        page_size: int = 100,
        cache_ttl: Optional[int] = None,
        current_user: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Cache all instances from DCIM API incrementally with pagination
        
        Args:
            page_size: Number of instances per page
            cache_ttl: Time to live for cache in seconds
            
        Returns:
            Dict with success status and statistics
        """
        try:
            logger.info("🗑️ Clearing old cache...")
            self.client.clear_cache()
            
            page = 1
            total_cached = 0
            total_from_api = 0
            
            endpoint = "/api/v1/instances/"
            params = {
                "page": page,
                "page_size": page_size, 
                "user_name": current_user.username if current_user.role == 'user' else None
            }
            
            while True:
                raw_data = self.client.get_single_page(
                    endpoint=endpoint,
                    params=params
                )
                
                if raw_data is None:
                    logger.error(f"❌ Failed to fetch page {page}, stopping...")
                    break
                
                instances = raw_data.get("instances", [])
                total_from_api = raw_data.get("total", 0)
                current_page = raw_data.get("page", page)
                total_pages = raw_data.get("total_pages", 0)
                
                logger.info(
                    f"✅ Page {current_page}/{total_pages}: "
                    f"fetched {len(instances)} instances"
                )
                
                if not instances:
                    logger.info("ℹ️ No more instances, stopping...")
                    break
                
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
                
                if current_page >= total_pages:
                    logger.info("✅ Reached last page, stopping...")
                    break
                
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
        """
        Get instances from cache
        
        Returns:
            List of cached instances or None if cache is empty
        """
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
            return Nones
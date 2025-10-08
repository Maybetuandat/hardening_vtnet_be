"""
File 1: dcim_service.py
Main service orchestrating DCIM operations
"""
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from client.dcim_client import dcim_client
from config.setting_redis import get_redis_settings

from models.user import User
from services.backend_cache_service import BackendCacheService
from services.dcim_sync_service import DCIMSyncService
from services.dcim_cache_service import DCIMCacheService

redis_settings = get_redis_settings()
logger = logging.getLogger(__name__)


class DCIMService:
    """Main service for DCIM operations"""

    def __init__(self, db: Session):
        self.client = dcim_client
        self.db = db
        self.backend_cache_service = BackendCacheService(db)
        self.cache_service = DCIMCacheService(dcim_client)
        self.sync_service = DCIMSyncService(db)

    def cache_all_instances_incrementally(
        self,
        page_size: int = 100,
        cache_ttl: Optional[int] = None,
        current_user: Optional[User] = None
    ) -> Dict[str, Any]:
        """Cache all instances from DCIM incrementally"""
        return self.cache_service.cache_all_instances_incrementally(
            page_size=page_size,
            cache_ttl=cache_ttl, 
            current_user=current_user
        )
    
    def get_cached_instances(self) -> Optional[List[Dict]]:
        """Get instances from cache"""
        return self.cache_service.get_cached_instances()

    def cache_data_from_backend_and_dcim(self, current_user: User):
        """
        Main sync logic between DCIM and Backend
        Handles both initial bulk import and normal sync
        """
        try:
            print("🔄 Starting DCIM sync...")
            
            # STEP 1: Cache DCIM data
            
            result = self.cache_all_instances_incrementally(
                page_size=100,
                cache_ttl=redis_settings.CACHE_TTL_DCIM_INSTANCES, current_user=current_user
            )
            
            if not result.get("success", False):
                logger.error("❌ Failed to sync data from DCIM")
                return None
            
            print(f"✅ DCIM sync completed: {result}")
            
            # STEP 2: Get cached DCIM instances
            cached_instance_data_from_dcim = self.get_cached_instances()

            if cached_instance_data_from_dcim is None:
                logger.error("❌ Failed to retrieve cached data after sync")
                return None

            print(f"✅ Processing {len(cached_instance_data_from_dcim)} instances from DCIM...")

            # STEP 3: Cache backend data
            backend_cache_result = self.backend_cache_service.cache_instances_to_redis()
              
            if not backend_cache_result.get("success", False):
                logger.error("❌ Failed to cache backend instances")
                return None
            
            # STEP 4: Get cached backend instances
            cached_backend_instances = self.backend_cache_service.get_cached_instances()
           
            # STEP 5: Handle NULL/EMPTY backend cache - Initial bulk import
            if cached_backend_instances is None or len(cached_backend_instances) == 0:
                print("\n" + "="*60)
                print("📦 Backend cache is EMPTY - Performing initial bulk import")
                print("="*60)
                
                return self.sync_service.bulk_import_from_dcim(
                    dcim_instances=cached_instance_data_from_dcim
                )
            
            # STEP 6: Normal sync (both caches exist)
            return self.sync_service.sync_instances_between_dcim_and_backend(
                dcim_instances=cached_instance_data_from_dcim,
                backend_instances=cached_backend_instances
            )
            
        except Exception as e:
            logger.error(f"❌ Error syncing data from DCIM: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
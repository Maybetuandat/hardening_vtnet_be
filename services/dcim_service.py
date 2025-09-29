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
    
   
   
    
    def cache_all_instances(self, use_cache: bool = True) -> Dict[str, Any]:
       
        number_of_record = 0
        page = 1
        page_size = 100  
        
        try:
            first_request = InstanceListRequest(
                page=page,
                page_size=page_size,
                use_cache=use_cache
            )
            
            first_result = self.get_instances(first_request)
            
            number_of_record += len(first_result.instances) if first_result else 0
            if first_result is None:
                logger.error("Failed to fetch first page of instances")
                return None
            
            
            
            total_pages = first_result.total_pages
            total = first_result.total
            
            logger.info(f"Starting to fetch all instances: total={total}, total_pages={total_pages}")
            
            # Fetch remaining pages
            while page < total_pages:
                page += 1
                
                next_request = InstanceListRequest(
                    page=page,
                    page_size=page_size,
                    use_cache=use_cache
                )
                
                next_result = self.get_instances(next_request)
                
                if next_result is None:
                    logger.warning(f"Failed to fetch page {page}, stopping pagination")
                    break
                
                
                
                


            logger.info(f"Successfully fetched all {number_of_record} instances")

            # Return all data with updated metadata
            return {
                "number_of_record": number_of_record
            }
            
        except Exception as e:
            logger.error(f"Error fetching all instances: {str(e)}")
            return None
 
    def get_instances(self, request: InstanceListRequest) -> Optional[InstanceListResponseFromDcim]:
       
        try:
            if request.page < 1:
                logger.warning(f"Invalid page number: {request.page}")
                return None
            
            
            
            endpoint = "/api/v1/instances/"
            params = {
                "page": request.page,
                "page_size": request.page_size
            }
            
            raw_data = self.client.get(
                endpoint=endpoint,
                params=params,
                use_cache=request.use_cache,
                cache_ttl=redis_settings.CACHE_TTL_DCIM_INSTANCES
            )
            
            if raw_data is None:
                logger.error("Failed to fetch instances from DCIM")
                return None
            
            
            logger.info(f"Raw data keys: {raw_data.keys()}")
            
            # ✅ Transform: Map field names từ DCIM response sang schema
            transformed_data = {
                "instances": raw_data.get("instances", []),  
                "total_instances": raw_data.get("total", 0), 
                "page": raw_data.get("page", request.page),
                "page_size": raw_data.get("page_size", request.page_size),
                "total": raw_data.get("total", 0),
                "total_pages": raw_data.get("total_pages", 0)
            }
            
           
            
            
            response = InstanceListResponseFromDcim(**transformed_data)
            
            
            return response
            
        except Exception as e:
            logger.error(f"Error in get_instances service: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
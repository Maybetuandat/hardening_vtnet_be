from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from sqlalchemy.orm import Session
from config.config_database import get_db
from schemas.instance import  InstanceListResponseFromDcim
from services.dcim_service import DCIMService

router = APIRouter(prefix="/api/dcim", tags=["DCIM"])


def get_dcim_service(db: Session = Depends(get_db)) -> DCIMService:
    return DCIMService(db)


@router.get("/instances")
def get_instances(
    
    
    
    dcim_service: DCIMService = Depends(get_dcim_service)
):
 
    try:
        
        
        result = dcim_service.cache_data_from_backend_and_dcim()
        
        if result is None:
            raise HTTPException(
                status_code=500, 
                detail="Failed to fetch instances from DCIM"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


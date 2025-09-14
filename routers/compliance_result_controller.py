from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from config.config_database import get_db
from schemas.compliance_result import (
    ComplianceResultResponse, 
    ComplianceResultListResponse, ComplianceScanRequest,
    ComplianceScanResponse, ComplianceSearchParams
)
from services.compilance_result_service import ComplianceResultService
from services.scan_service import ScanService
from utils.auth import require_admin, require_user


router = APIRouter(prefix="/api/compliance", tags=["Compliance"])


def get_compliance_service(db: Session = Depends(get_db),
                           current_user = Depends(require_user())) -> ComplianceResultService:
    return ComplianceResultService(db)

def get_scan_service(db: Session = Depends(get_db), current_user = Depends(require_user())) -> ScanService:
    return ScanService(db)

@router.get("/", response_model=ComplianceResultListResponse)
def get_compliance_results(
    keyword: Optional[str] = Query(None, description="Từ khóa tìm kiếm theo ip server"),
    today: Optional[str] = Query(None, description="Lọc kết quả của hôm nay"),
    
    status: Optional[str] = Query(None, description="Filter theo trạng thái"),
    page: int = Query(1, ge=1, description="Số trang"),
    page_size: int = Query(10, ge=1, le=100, description="Số lượng item mỗi trang"),
    compliance_service: ComplianceResultService = Depends(get_compliance_service),
    current_user = Depends(require_user())
    
):
   
    try:
        search_params = ComplianceSearchParams(
            
            today=today,
            keyword=keyword,
            status=status,
            page=page,
            page_size=page_size
        )
        return compliance_service.get_compliance_results(search_params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





@router.get("/{compliance_id}", response_model=ComplianceResultResponse)
def get_compliance_result_detail(
    compliance_id: int,
    compliance_service: ComplianceResultService = Depends(get_compliance_service),
    current_user = Depends(require_user())
):
   
    try:
        result = compliance_service.get_by_id(compliance_id)
        if not result:
            raise HTTPException(status_code=404, detail="Compliance result không tìm thấy")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan", response_model=ComplianceScanResponse)
def start_compliance_scan(
    scan_request: ComplianceScanRequest,
    scan_service: ScanService = Depends(get_scan_service),
    current_user = Depends(require_user())
):
   
    try:
        # Validate batch_size
        if scan_request.batch_size > 50:
            raise HTTPException(
                status_code=400, 
                detail="Batch size tối đa là 50 servers"
            )
            
   
        return scan_service.start_compliance_scan(scan_request)
        
        
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))






@router.delete("/{compliance_id}")
def delete_compliance_result(
    compliance_id: int,
    compliance_service: ComplianceResultService = Depends(get_compliance_service),
    current_user = Depends(require_admin())
):
   
    try:
        success = compliance_service.delete_compliance_result(compliance_id)
        if not success:
            raise HTTPException(status_code=404, detail="Compliance result không tìm thấy")
        
        return {"message": "Xóa compliance result thành công"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
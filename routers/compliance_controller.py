from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from config.config_database import get_db
from schemas.compliance import (
    ComplianceResultResponse, ComplianceResultDetailResponse,
    ComplianceResultListResponse, ComplianceScanRequest,
    ComplianceScanResponse, ComplianceSearchParams
)
from services.compilance_result_service import ComplianceResultService
from services.scan_service import ScanService


router = APIRouter(prefix="/api/compliance", tags=["Compliance"])


def get_compliance_service(db: Session = Depends(get_db)) -> ComplianceResultService:
    return ComplianceResultService(db)

def get_scan_service(db: Session = Depends(get_db)) -> ScanService:
    return ScanService(db)

@router.get("/", response_model=ComplianceResultListResponse)
def get_compliance_results(
    keyword: Optional[str] = Query(None, description="Từ khóa tìm kiếm theo ip server"),
    server_id: Optional[int] = Query(None, description="ID của server"),
    status: Optional[str] = Query(None, description="Filter theo trạng thái"),
    page: int = Query(1, ge=1, description="Số trang"),
    page_size: int = Query(10, ge=1, le=100, description="Số lượng item mỗi trang"),
    compliance_service: ComplianceResultService = Depends(get_compliance_service)
):
    """
    Lấy danh sách kết quả compliance
    """
    try:
        search_params = ComplianceSearchParams(
            
            keyword=keyword,
            status=status,
            page=page,
            page_size=page_size
        )
        return compliance_service.get_compliance_results(search_params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





@router.get("/{compliance_id}", response_model=ComplianceResultDetailResponse)
def get_compliance_result_detail(
    compliance_id: int,
    compliance_service: ComplianceResultService = Depends(get_compliance_service)
):
    """
    Lấy chi tiết kết quả compliance bao gồm rule results
    """
    try:
        result = compliance_service.get_compliance_result_detail(compliance_id)
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
    scan_service: ScanService = Depends(get_scan_service)
):
    """
    Bắt đầu quét compliance cho servers theo batch
    
    - server_ids: Danh sách server IDs cụ thể (None = scan all servers)
    
    - batch_size: Số servers mỗi batch (default: 100, max: 500)
    """
    try:
        # Validate batch_size
        if scan_request.batch_size > 500:
            raise HTTPException(
                status_code=400, 
                detail="Batch size tối đa là 500 servers"
            )
            
        # Validate server_ids if provided
        if scan_request.server_ids and len(scan_request.server_ids) > 1000:
            raise HTTPException(
                status_code=400,
                detail="Số lượng server tối đa là 1000"
            )

        result = scan_service.start_compliance_scan(scan_request)
        print("DEBUG result:", result)
        return result
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))






@router.delete("/{compliance_id}")
def delete_compliance_result(
    compliance_id: int,
    compliance_service: ComplianceResultService = Depends(get_compliance_service)
):
    """
    Xóa kết quả compliance
    """
    try:
        success = compliance_service.dao.delete(compliance_id)
        if not success:
            raise HTTPException(status_code=404, detail="Compliance result không tìm thấy")
        
        return {"message": "Xóa compliance result thành công"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import io

from config.config_database import get_db
from schemas.compliance_result import ComplianceSearchParams
from services.export_service import ExportService


router = APIRouter(prefix="/api/export", tags=["Export"])


def get_export_service(db: Session = Depends(get_db)) -> ExportService:
    return ExportService(db)


@router.get("/compliance/excel")
async def export_compliance_to_excel(
    keyword: Optional[str] = Query(None, description="Từ khóa tìm kiếm theo ip server"),
    list_workload_id: Optional[List[int]] = Query(None, description="Danh sach ID workload"),
    status: Optional[str] = Query(None, description="Filter theo trạng thái"),
    export_service: ExportService = Depends(get_export_service)
):
    """
    Xuất báo cáo compliance results trong ngày hiện tại ra file Excel
    """
    try:
        
        search_params = None
        if keyword or list_workload_id or status:
            search_params = ComplianceSearchParams(
                list_workload_id=list_workload_id,
                keyword=keyword,  # keyword chi tim kiem theo nhom node 
                status=status,
                page=1,
                page_size=100
            )
        
        
        excel_bytes = export_service.export_compliance_results_to_excel(search_params)
        
        
        filename = export_service.get_export_filename()
        
        
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xuất báo cáo: {str(e)}")
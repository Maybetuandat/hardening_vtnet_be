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

# @router.get("/", response_model=ComplianceResultListResponse)
# def get_compliance_results(
#     server_id: Optional[int] = Query(None, description="Filter theo server ID"),
#     workload_id: Optional[int] = Query(None, description="Filter theo workload ID"),
#     status: Optional[str] = Query(None, description="Filter theo trạng thái"),
#     page: int = Query(1, ge=1, description="Số trang"),
#     page_size: int = Query(10, ge=1, le=100, description="Số lượng item mỗi trang"),
#     compliance_service: ComplianceResultService = Depends(get_compliance_service)
# ):
#     """
#     Lấy danh sách kết quả compliance
#     """
#     try:
#         search_params = ComplianceSearchParams(
#             server_id=server_id,
#             workload_id=workload_id,
#             status=status,
#             page=page,
#             page_size=page_size
#         )
#         return compliance_service.get_compliance_results(search_params)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/server/{server_id}/history")
# def get_server_compliance_history(
#     server_id: int,
#     limit: int = Query(10, ge=1, le=50, description="Số lượng records trả về"),
#     compliance_service: ComplianceResultService = Depends(get_compliance_service)
# ):
#     """
#     Lấy lịch sử compliance của một server
#     """
#     try:
#         history = compliance_service.get_server_compliance_history(server_id, limit)
#         return {
#             "server_id": server_id,
#             "compliance_history": history,
#             "total_scans": len(history)
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/workload/{workload_id}/summary")
# def get_workload_compliance_summary(
#     workload_id: int,
#     compliance_service: ComplianceResultService = Depends(get_compliance_service)
# ):
#     """
#     Lấy tổng quan compliance của một workload
#     """
#     try:
#         summary = compliance_service.get_compliance_summary_by_workload(workload_id)
#         return summary
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.get("/{compliance_id}", response_model=ComplianceResultDetailResponse)
# def get_compliance_result_detail(
#     compliance_id: int,
#     compliance_service: ComplianceResultService = Depends(get_compliance_service)
# ):
#     """
#     Lấy chi tiết kết quả compliance bao gồm rule results
#     """
#     try:
#         result = compliance_service.get_compliance_result_detail(compliance_id)
#         if not result:
#             raise HTTPException(status_code=404, detail="Compliance result không tìm thấy")
#         return result
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@router.post("/scan", response_model=ComplianceScanResponse)
def start_compliance_scan(
    scan_request: ComplianceScanRequest,
    scan_service: ScanService = Depends(get_scan_service)
):
    """
    Bắt đầu quét compliance cho servers theo batch
    
    - server_ids: Danh sách server IDs cụ thể (None = scan all servers)
    - workload_id: Filter theo workload (optional)  
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


# @router.post("/scan/all", response_model=ComplianceScanResponse)
# def scan_all_servers(
#     batch_size: int = Query(100, ge=1, le=500, description="Số servers mỗi batch"),
#     compliance_service: ComplianceResultService = Depends(get_compliance_service)
# ):
#     """
#     Quét compliance cho TẤT CẢ servers active trong database
#     Sử dụng pagination để bốc đại servers, không care workload
#     """
#     try:
#         scan_request = ComplianceScanRequest(
#             server_ids=None,  # Scan all
#             batch_size=batch_size
#         )
        
#         result = compliance_service.start_compliance_scan(scan_request)
#         return result
        
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/scan/servers", response_model=ComplianceScanResponse)
# def scan_specific_servers(
#     request_body: dict,  # Nhận body để lấy server_ids
#     batch_size: int = Query(50, ge=1, le=200, description="Số servers mỗi batch cho specific list"),
#     compliance_service: ComplianceResultService = Depends(get_compliance_service)
# ):
#     """
#     Quét compliance cho danh sách servers cụ thể
#     Body: {"server_ids": [1, 2, 3, 4, 5]}
#     """
#     try:
#         server_ids = request_body.get("server_ids", [])
        
#         if not server_ids:
#             raise HTTPException(status_code=400, detail="Danh sách server_ids không được rỗng")
            
#         if len(server_ids) > 10000:
#             raise HTTPException(status_code=400, detail="Số lượng server tối đa là 10,000")

#         # Remove duplicates
#         unique_server_ids = list(set(server_ids))
        
#         scan_request = ComplianceScanRequest(
#             server_ids=unique_server_ids,
#             batch_size=min(batch_size, 200)  # Giới hạn batch_size cho specific list
#         )
        
#         result = compliance_service.start_compliance_scan(scan_request)
#         return result
        
#     except HTTPException:
#         raise
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/scan/preview")
# def preview_compliance_scan(
#     scan_request: ComplianceScanRequest,
#     compliance_service: ComplianceResultService = Depends(get_compliance_service)
# ):
#     """
#     Preview thông tin scan trước khi thực hiện
#     Cho biết sẽ scan bao nhiêu servers, estimated time, etc.
#     """
#     try:
#         # Count servers
#         total_servers = compliance_service._count_servers_for_scan(scan_request)
        
#         if total_servers == 0:
#             raise HTTPException(status_code=400, detail="Không có server nào để scan")
        
#         # Estimate scan time (rough calculation)
#         estimated_time_per_server = 30  # seconds
#         estimated_total_seconds = total_servers * estimated_time_per_server
#         estimated_hours = estimated_total_seconds // 3600
#         estimated_minutes = (estimated_total_seconds % 3600) // 60
        
#         # Get server statistics
#         server_stats = compliance_service.server_dao.get_servers_statistics()
        
#         scan_mode = "specific_list" if scan_request.server_ids else "all_servers"
#         num_batches = (total_servers + scan_request.batch_size - 1) // scan_request.batch_size
        
#         return {
#             "scan_mode": scan_mode,
#             "total_servers": total_servers,
#             "batch_size": scan_request.batch_size,
#             "estimated_batches": num_batches,
#             "estimated_duration": {
#                 "hours": estimated_hours,
#                 "minutes": estimated_minutes,
#                 "total_seconds": estimated_total_seconds
#             },
#             "server_breakdown": {
#                 "by_workload": server_stats.get("workload_breakdown", []),
#                 "by_os": server_stats.get("os_breakdown", [])
#             } if not scan_request.server_ids else None,
#             "warnings": [
#                 "Scan có thể mất nhiều thời gian với database lớn",
#                 "Scan sẽ chạy trong background, bạn có thể theo dõi progress"
#             ] if total_servers > 1000 else []
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


# @router.delete("/{compliance_id}")
# def delete_compliance_result(
#     compliance_id: int,
#     compliance_service: ComplianceResultService = Depends(get_compliance_service)
# ):
#     """
#     Xóa kết quả compliance
#     """
#     try:
#         success = compliance_service.dao.delete(compliance_id)
#         if not success:
#             raise HTTPException(status_code=404, detail="Compliance result không tìm thấy")
        
#         return {"message": "Xóa compliance result thành công"}
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
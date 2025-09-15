from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.config_database import get_db
from schemas.setting import ScanScheduleRequest, ScanScheduleResponse
from services.scheduler_singleton import SchedulerSingleton
from utils.auth import require_admin, require_user



router = APIRouter(prefix="/api/scheduler", tags=["Scheduler"])


def get_scheduler_service(db: Session = Depends(get_db), current_user=Depends(require_user())):
    """Get singleton scheduler service - LUÔN CÙNG 1 INSTANCE"""
    return SchedulerSingleton.get_instance(db)


@router.get("/", response_model=ScanScheduleResponse)
def get_scan_schedule(
    scheduler_service = Depends(get_scheduler_service),
    current_user = Depends(require_user())
):
    """Lấy thông tin lịch scan hiện tại"""
    try:
        return scheduler_service.get_scan_schedule()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/", response_model=ScanScheduleResponse)
def update_scan_schedule(
    request: ScanScheduleRequest,
    scheduler_service = Depends(get_scheduler_service),
    current_user = Depends(require_user())
):
    """
    Cập nhật lịch scan tự động
    FIXED: Sử dụng singleton nên APScheduler sẽ được update đúng
    """
    try:
        print(f"🔄 Updating scan schedule: {request.scan_time}, enabled: {request.is_enabled}")
        
        # Update DB + Reschedule APScheduler job  
        result = scheduler_service.update_scan_schedule(request)
        
        # Debug: Verify job was rescheduled
        scan_job = scheduler_service.scheduler.get_job(scheduler_service.scan_job_id)
        if scan_job and request.is_enabled:
            print(f"✅ Job rescheduled successfully. Next run: {scan_job.next_run_time}")
        elif not request.is_enabled:
            print("⏸️ Job disabled successfully")
        else:
            print("⚠️ Warning: Job may not be scheduled properly")
            
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Error updating schedule: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/status")
def get_scheduler_status(
    scheduler_service = Depends(get_scheduler_service),
    current_user = Depends(require_user())
):
    """Lấy trạng thái của scheduler và job hiện tại"""
    try:
        schedule_info = scheduler_service.get_scan_schedule()
        
        is_running = scheduler_service.scheduler.running
        job = scheduler_service.scheduler.get_job(scheduler_service.scan_job_id)
        
        return {
            "scheduler_running": is_running,
            "job_exists": job is not None,
            "job_next_run": job.next_run_time.isoformat() if job and job.next_run_time else None,
            "scan_schedule": {
                "scan_time": schedule_info.scan_time,
                "is_enabled": schedule_info.is_enabled,
                "next_run": schedule_info.next_run.isoformat() if schedule_info.next_run else None,
                "last_run": schedule_info.last_run.isoformat() if schedule_info.last_run else None
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/")
def disable_scan_schedule(
    scheduler_service = Depends(get_scheduler_service),
    current_user = Depends(require_user())
):
    """Tắt hoàn toàn lịch scan tự động"""
    try:
        request = ScanScheduleRequest(scan_time="00:00", is_enabled=False)
        result = scheduler_service.update_scan_schedule(request)
        
        return {
            "message": "Đã tắt lịch scan tự động thành công",
            "scan_time": result.scan_time,
            "is_enabled": result.is_enabled,
            "success": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# @router.get("/debug")
# def debug_scheduler(
#     scheduler_service = Depends(get_scheduler_service)
# ):
#     """Debug scheduler - kiểm tra trạng thái chi tiết"""
#     try:
#         debug_info = scheduler_service.get_debug_info()
        
#         # Thêm info về singleton
#         debug_info["singleton_initialized"] = SchedulerSingleton.is_initialized()
#         debug_info["singleton_instance_id"] = id(scheduler_service)
        
#         return debug_info
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")



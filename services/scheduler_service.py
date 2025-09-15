import logging
import requests
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from dao.setting_dao import SettingsDAO
from schemas.compliance_result import ComplianceScanRequest
from schemas.setting import ScanScheduleRequest, ScanScheduleResponse
from services import scan_service
from services.scan_service import ScanService





class SchedulerService:
    def __init__(self, db: Session):
        self.db = db
        self.settings_dao = SettingsDAO(db)
        self.scheduler = BackgroundScheduler()
        self.scan_job_id = "daily_hardening_scan"
        self.scan_service = ScanService(db)
        
    def start_scheduler(self):
        try:
            self.scheduler.start()
            logging.info("✅ APScheduler started successfully")
            
            
            self._load_scan_schedule_from_db()
            
        except Exception as e:
            logging.error(f" Error starting scheduler: {str(e)}")

    def stop_scheduler(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logging.info(" APScheduler stopped")

    def update_scan_schedule(self, request: ScanScheduleRequest) -> ScanScheduleResponse:
        
        try:
            
            self.settings_dao.set_scan_schedule(request.scan_time, request.is_enabled)
            
            
            self._reschedule_scan_job(request.scan_time, request.is_enabled)
            
            
            next_run = self._calculate_next_run_time(request.scan_time) if request.is_enabled else None
            
            return ScanScheduleResponse(
                scan_time=request.scan_time,
                is_enabled=request.is_enabled,
                next_run=next_run,
                last_run=self._get_last_run_time(),
                message=f"Đã {'bật' if request.is_enabled else 'tắt'} lịch scan tự động lúc {request.scan_time}"
            )
            
        except Exception as e:
            logging.error(f"Error updating scan schedule: {str(e)}")
            raise e

    def get_scan_schedule(self) -> ScanScheduleResponse:
        
        config = self.settings_dao.get_scan_schedule()
        
        next_run = None
        if config["is_enabled"]:
            next_run = self._calculate_next_run_time(config["scan_time"])
            
        return ScanScheduleResponse(
            scan_time=config["scan_time"],
            is_enabled=config["is_enabled"],
            next_run=next_run,
            last_run=self._get_last_run_time(),
            message="Thông tin lịch scan hiện tại"
        )

    def _load_scan_schedule_from_db(self):
        try:
            config = self.settings_dao.get_scan_schedule()
            
            if config["is_enabled"]:
                self._reschedule_scan_job(config["scan_time"], True)
                logging.info(f" Loaded scan schedule from DB: {config['scan_time']} (enabled)")
            else:
                logging.info(" Scan schedule is disabled in DB")
                
        except Exception as e:
            logging.error(f"Error loading scan schedule from DB: {str(e)}")

    def _reschedule_scan_job(self, scan_time: str, is_enabled: bool):
        # Remove existing job nếu có
        if self.scheduler.get_job(self.scan_job_id):
            self.scheduler.remove_job(self.scan_job_id)
            logging.info(f" Removed existing scan job")

        if is_enabled:
            # Parse time
            hour, minute = map(int, scan_time.split(':'))
            
            # Add new job
            self.scheduler.add_job(
                func=self._execute_hardening_scan,
                trigger=CronTrigger(hour=hour, minute=minute),
                id=self.scan_job_id,
                name=f"Daily Hardening Scan at {scan_time}",
                replace_existing=True,
                misfire_grace_time=300 
            )
            
            logging.info(f" Scheduled daily hardening scan at {scan_time}")
        else:
            logging.info("Scan schedule disabled - no job added")

    def _execute_hardening_scan(self):
        
        try:
            logging.info(" Starting scheduled hardening scan...")
            
            scan_request = ComplianceScanRequest(batch_size=10)
            
            self.scan_service.start_compliance_scan(scan_request)
            
           
                
                
            self._save_last_run_time()
                
            
                
        except requests.exceptions.RequestException as e:
            logging.error(f" Network error during scheduled scan: {str(e)}")
        except Exception as e:
            logging.error(f" Unexpected error during scheduled scan: {str(e)}")

    def _calculate_next_run_time(self, scan_time: str) -> datetime:
        
        hour, minute = map(int, scan_time.split(':'))
        
        now = datetime.now()
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        
        if next_run <= now:
            next_run += timedelta(days=1)
            
        return next_run

    def _save_last_run_time(self):
        
        self.settings_dao.create_or_update(
            key="scan_last_run_time",
            value=datetime.now().isoformat(),
            description="Thời gian chạy scan gần nhất"
        )

    def _get_last_run_time(self) -> Optional[datetime]:
        
        try:
            setting = self.settings_dao.get_by_key("scan_last_run_time")
            if setting:
                return datetime.fromisoformat(setting.value)
        except Exception:
            pass
        return None

   


    def get_debug_info(self):
        """Lấy thông tin debug của scheduler"""
        try:
            jobs = self.scheduler.get_jobs()
            scan_job = self.scheduler.get_job(self.scan_job_id)
            
            return {
                "scheduler_running": self.scheduler.running,
                "scheduler_state": str(self.scheduler.state),
                "total_jobs": len(jobs),
                "scan_job_exists": scan_job is not None,
                "scan_job_id": self.scan_job_id,
                "next_run_time": scan_job.next_run_time.isoformat() if scan_job and scan_job.next_run_time else None,
                "current_time": datetime.now().isoformat(),
                "current_utc_time": datetime.utcnow().isoformat(),
                "db_config": self.settings_dao.get_scan_schedule(),
                "jobs_detail": [
                    {
                        "id": job.id,
                        "name": job.name,
                        "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                        "trigger": str(job.trigger)
                    }
                    for job in jobs
                ]
            }
        except Exception as e:
            return {
                "error": f"Debug info failed: {str(e)}",
                "scheduler_running": getattr(self.scheduler, 'running', False) if hasattr(self, 'scheduler') else False
            }
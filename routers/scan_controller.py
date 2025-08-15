# routers/scan_controller.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from config.config_database import get_db
from services.scan_service import ScanService
from pydantic import BaseModel
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scan", tags=["Scan"])


class SimpleScanRequest(BaseModel):
    server_id: int


class ComplianceScanRequest(BaseModel):
    server_id: int
    security_standard_id: int


class ScanResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


@router.post("/simple", response_model=ScanResponse)
async def simple_scan(
    request: SimpleScanRequest,
    db: Session = Depends(get_db)
):
    """
    Thực hiện scan đơn giản với các lệnh cơ bản như pwd, whoami
    """
    try:
        logger.info(f"Starting simple scan for server ID: {request.server_id}")
        
        result = await ScanService.simple_scan(db, request.server_id)
        
        logger.info(f"Simple scan completed for server ID: {request.server_id}")
        
        return ScanResponse(
            success=True,
            message="Simple scan completed successfully",
            data=result
        )
        
    except HTTPException as e:
        logger.error(f"HTTP error during simple scan: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during simple scan: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simple scan failed: {str(e)}"
        )


@router.post("/compliance", response_model=ScanResponse)
async def compliance_scan(
    request: ComplianceScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Thực hiện scan tuân thủ bảo mật với Ansible
    Sử dụng SSH key để kết nối đến server, thực thi các lệnh ansible theo OS version,
    so sánh kết quả với tham số mặc định trong rule và trả về kết quả
    """
    try:
        logger.info(f"Starting compliance scan for server ID: {request.server_id}, "
                   f"security standard ID: {request.security_standard_id}")
        
        # Thực hiện scan (có thể mất thời gian nên có thể chạy background)
        result = await ScanService.compliance_scan(
            db, 
            request.server_id, 
            request.security_standard_id
        )
        
        logger.info(f"Compliance scan completed for server ID: {request.server_id}")
        
        return ScanResponse(
            success=True,
            message="Compliance scan completed successfully",
            data=result
        )
        
    except HTTPException as e:
        logger.error(f"HTTP error during compliance scan: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during compliance scan: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compliance scan failed: {str(e)}"
        )


@router.post("/compliance/async", response_model=ScanResponse)
async def compliance_scan_async(
    request: ComplianceScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Thực hiện scan tuân thủ bảo mật với Ansible (chạy background)
    """
    try:
        logger.info(f"Starting async compliance scan for server ID: {request.server_id}")
        
        # Thêm task vào background
        background_tasks.add_task(
            ScanService.compliance_scan,
            db,
            request.server_id,
            request.security_standard_id
        )
        
        return ScanResponse(
            success=True,
            message="Compliance scan started in background",
            data={
                "server_id": request.server_id,
                "security_standard_id": request.security_standard_id,
                "status": "started"
            }
        )
        
    except Exception as e:
        logger.error(f"Error starting async compliance scan: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start compliance scan: {str(e)}"
        )


@router.get("/results/{compliance_result_id}")
async def get_scan_result(
    compliance_result_id: int,
    db: Session = Depends(get_db)
):
    """
    Lấy kết quả scan theo compliance_result_id
    """
    try:
        from models.compliance_result import ComplianceResult
        from models.rule_result import RuleResult
        from models.rule import Rule
        
        # Lấy compliance result
        compliance_result = db.query(ComplianceResult).filter(
            ComplianceResult.id == compliance_result_id
        ).first()
        
        if not compliance_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan result not found"
            )
        
        # Lấy rule results
        rule_results = db.query(RuleResult).filter(
            RuleResult.compliance_result_id == compliance_result_id
        ).all()
        
        # Lấy thông tin rules
        rule_details = []
        for rule_result in rule_results:
            rule = db.query(Rule).filter(Rule.id == rule_result.rule_id).first()
            rule_details.append({
                "rule_id": rule_result.rule_id,
                "rule_name": rule.name if rule else "Unknown",
                "rule_description": rule.description if rule else "",
                "severity": rule.severity if rule else "medium",
                "status": rule_result.status,
                "message": rule_result.message,
                "details": rule_result.details,
                "created_at": rule_result.created_at.isoformat()
            })
        
        return ScanResponse(
            success=True,
            message="Scan result retrieved successfully",
            data={
                "compliance_result_id": compliance_result.id,
                "server_id": compliance_result.server_id,
                "security_standard_id": compliance_result.security_standard_id,
                "status": compliance_result.status,
                "total_rules": compliance_result.total_rules,
                "passed_rules": compliance_result.passed_rules,
                "failed_rules": compliance_result.failed_rules,
                "score": compliance_result.score,
                "scan_date": compliance_result.scan_date.isoformat(),
                "rule_results": rule_details
            }
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving scan result: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve scan result: {str(e)}"
        )


@router.get("/results/server/{server_id}")
async def get_server_scan_history(
    server_id: int,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Lấy lịch sử scan của một server
    """
    try:
        from models.compliance_result import ComplianceResult
        from models.security_standard import SecurityStandard
        
        # Lấy compliance results của server
        query = db.query(ComplianceResult).filter(
            ComplianceResult.server_id == server_id
        ).order_by(ComplianceResult.scan_date.desc())
        
        total = query.count()
        compliance_results = query.offset(skip).limit(limit).all()
        
        # Lấy thông tin security standards
        results = []
        for result in compliance_results:
            security_standard = db.query(SecurityStandard).filter(
                SecurityStandard.id == result.security_standard_id
            ).first()
            
            results.append({
                "compliance_result_id": result.id,
                "security_standard_name": security_standard.name if security_standard else "Unknown",
                "security_standard_version": security_standard.version if security_standard else "",
                "status": result.status,
                "total_rules": result.total_rules,
                "passed_rules": result.passed_rules,
                "failed_rules": result.failed_rules,
                "score": result.score,
                "scan_date": result.scan_date.isoformat(),
                "created_at": result.created_at.isoformat()
            })
        
        return ScanResponse(
            success=True,
            message="Server scan history retrieved successfully",
            data={
                "server_id": server_id,
                "total": total,
                "results": results,
                "pagination": {
                    "skip": skip,
                    "limit": limit,
                    "has_more": (skip + limit) < total
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error retrieving server scan history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve server scan history: {str(e)}"
        )


@router.post("/test-connection")
async def test_server_connection(
    request: SimpleScanRequest,
    db: Session = Depends(get_db)
):
    """
    Test kết nối SSH đến server
    """
    try:
        logger.info(f"Testing connection to server ID: {request.server_id}")
        
        # Sử dụng simple scan với command đơn giản để test connection
        result = await ScanService.simple_scan(db, request.server_id)
        
        # Kiểm tra nếu ít nhất 1 command thành công
        success_count = sum(1 for cmd_result in result["results"].values() 
                          if cmd_result["success"])
        
        if success_count > 0:
            return ScanResponse(
                success=True,
                message="Connection test successful",
                data={
                    "server_id": request.server_id,
                    "connection_status": "success",
                    "successful_commands": success_count,
                    "total_commands": len(result["results"])
                }
            )
        else:
            return ScanResponse(
                success=False,
                message="Connection test failed - no commands executed successfully",
                data={
                    "server_id": request.server_id,
                    "connection_status": "failed",
                    "errors": [cmd_result["error"] for cmd_result in result["results"].values() 
                              if not cmd_result["success"]]
                }
            )
        
    except Exception as e:
        logger.error(f"Connection test failed for server ID {request.server_id}: {str(e)}")
        return ScanResponse(
            success=False,
            message=f"Connection test failed: {str(e)}",
            data={
                "server_id": request.server_id,
                "connection_status": "error",
                "error": str(e)
            }
        )
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.config_database import get_db
from schemas.fix_execution import ServerFixRequest, ServerFixResponse
from services.fix_service import FixService
from utils.auth import require_user


router = APIRouter(prefix="/api/fixes", tags=["Fix Execution"])


def get_fix_service(db: Session = Depends(get_db)) -> FixService:
    return FixService(db)


@router.post("/server", response_model=ServerFixResponse)
def execute_server_fixes(
    request: ServerFixRequest,
    fix_service: FixService = Depends(get_fix_service),
    current_user = Depends(require_user())
):
    """
    Execute fixes for multiple rule results on a single server.
    All fix commands will be grouped into one playbook for efficiency.
    
    - **server_id**: ID of the server to apply fixes
    - **rule_result_ids**: List of rule result IDs to fix (must belong to the specified server)
    
    The service will:
    1. Validate that all rule results belong to the specified server
    2. Check that rule results have "failed" status
    3. Check that corresponding rules have suggested_fix commands
    4. Group all valid fix commands into a single Ansible playbook
    5. Execute the playbook on the server
    6. Update rule results to "passed" status for successful fixes
    """
    try:
        if not request.rule_result_ids:
            raise HTTPException(
                status_code=400, 
                detail="rule_result_ids list cannot be empty"
            )
        
        return fix_service.execute_server_fixes(request)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing server fixes: {str(e)}")


@router.get("/server/{server_id}/fixable-rules")
def get_fixable_rules_for_server(
    server_id: int,
    fix_service: FixService = Depends(get_fix_service),
    current_user = Depends(require_user())
):
    """
    Get list of rule results that can be fixed for a specific server.
    Returns only rule results with "failed" status that have corresponding suggested_fix commands.
    """
    try:
        # This would be a helper method to get fixable rule results
        # Implementation would query rule_results with status="failed" for the server
        # and check if their rules have suggested_fix commands
        
        from dao.rule_result_dao import RuleResultDAO
        from dao.compliance_result_dao import ComplianceDAO
        from dao.rule_dao import RuleDAO
        
        db = next(get_db())
        try:
            rule_result_dao = RuleResultDAO(db)
            compliance_dao = ComplianceDAO(db)
            rule_dao = RuleDAO(db)
            
            # Get all compliance results for this server
            # (This would need a method in ComplianceDAO to get by server_id)
            # For now, this is a simplified approach
            
            fixable_rules = []
            # You would implement the logic here to find fixable rule results
            
            return {
                "server_id": server_id,
                "fixable_rule_results": fixable_rules,
                "total_fixable": len(fixable_rules)
            }
        finally:
            db.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting fixable rules: {str(e)}")
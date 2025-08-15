from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from config.config_database import get_db
from schemas.rule_schemas import RuleCreate, RuleResponse, RuleUpdate, RuleWithSecurityStandardResponse
from services.rule_service import RuleService

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rules", tags=["Rules"])


@router.get("", response_model=List[RuleWithSecurityStandardResponse])
async def get_all_rules(
    security_standard_id: int = Query(None, description="Filter by security standard ID"),
    severity: str = Query(None, description="Filter by severity"),
    active_only: bool = Query(False, description="Get only active rules"),
    db: Session = Depends(get_db)
):
    """Get all rules with optional filtering"""
    try:
        if active_only:
            rules = RuleService.get_active_rules(db)
        elif security_standard_id:
            # For security standard filter, use the basic response without security standard info
            basic_rules = RuleService.get_rules_by_security_standard(db, security_standard_id)
            # Convert to response with security standard info
            rules = []
            for rule_response in basic_rules:
                # Get the full rule and convert
                full_rule = RuleService.get_rule_by_id(db, rule_response.id)
                if full_rule:
                    rules.append(full_rule)
        elif severity:
            rules = RuleService.get_rules_by_severity(db, severity)
        else:
            rules = RuleService.get_all_rules(db)
        
        return rules
    except Exception as e:
        logger.error(f"Error fetching rules: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch rules: {str(e)}"
        )


@router.get("/{rule_id}", response_model=RuleWithSecurityStandardResponse)
async def get_rule(rule_id: int, db: Session = Depends(get_db)):
    """Get rule by ID"""
    try:
        rule = RuleService.get_rule_by_id(db, rule_id)
        if not rule:
            logger.warning(f"Rule with ID {rule_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rule not found"
            )
        return rule
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch rule: {str(e)}"
        )


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(rule_data: RuleCreate, db: Session = Depends(get_db)):
    """Create a new rule"""
    try:
        rule = RuleService.create_rule(db, rule_data)
        logger.info(f"Rule created successfully: {rule.name}")
        return rule
    except ValueError as e:
        logger.error(f"Validation error creating rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create rule: {str(e)}"
        )


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: int, 
    rule_data: RuleUpdate, 
    db: Session = Depends(get_db)
):
    """Update an existing rule"""
    try:
        updated_rule = RuleService.update_rule(db, rule_id, rule_data)
        if not updated_rule:
            logger.warning(f"Rule with ID {rule_id} not found for update")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rule not found"
            )
        logger.info(f"Rule with ID {rule_id} updated successfully")
        return updated_rule
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update rule: {str(e)}"
        )


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    """Delete a rule"""
    try:
        success = RuleService.delete_rule(db, rule_id)
        if not success:
            logger.warning(f"Rule with ID {rule_id} not found for deletion")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rule not found"
            )
        logger.info(f"Rule with ID {rule_id} deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete rule: {str(e)}"
        )


@router.get("/security-standard/{security_standard_id}", response_model=List[RuleResponse])
async def get_rules_by_security_standard(security_standard_id: int, db: Session = Depends(get_db)):
    """Get all rules for a specific security standard"""
    try:
        rules = RuleService.get_rules_by_security_standard(db, security_standard_id)
        return rules
    except Exception as e:
        logger.error(f"Error fetching rules by security standard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch rules by security standard: {str(e)}"
        )


@router.get("/security-standard/{security_standard_id}/count")
async def get_rules_count_by_security_standard(security_standard_id: int, db: Session = Depends(get_db)):
    """Get number of rules for a specific security standard"""
    try:
        from dao.rule_dao import RuleDAO
        count = RuleDAO.get_rules_count_by_security_standard(db, security_standard_id)
        logger.info(f"Number of rules for security standard {security_standard_id}: {count}")
        return {"count": count}
    except Exception as e:
        logger.error(f"Error fetching rules count by security standard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch rules count by security standard: {str(e)}"
        )
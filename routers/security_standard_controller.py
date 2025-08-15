from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from config.config_database import get_db
from schemas.security_standard_schemas import SecurityStandardCreate, SecurityStandardResponse, SecurityStandardUpdate
from services.security_standard_service import SecurityStandardService

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/security-standards", tags=["Security Standards"])


@router.get("", response_model=List[SecurityStandardResponse])
async def get_all_security_standards(
    version: str = Query(None, description="Filter by version"),
    active_only: bool = Query(False, description="Get only active security standards"),
    db: Session = Depends(get_db)
):
    """Get all security standards with optional filtering"""
    try:
        if active_only:
            security_standards = SecurityStandardService.get_active_security_standards(db)
        elif version:
            security_standards = SecurityStandardService.get_security_standards_by_version(db, version)
        else:
            security_standards = SecurityStandardService.get_all_security_standards(db)
        
        return security_standards
    except Exception as e:
        logger.error(f"Error fetching security standards: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch security standards: {str(e)}"
        )


@router.get("/{security_standard_id}", response_model=SecurityStandardResponse)
async def get_security_standard(security_standard_id: int, db: Session = Depends(get_db)):
    """Get security standard by ID"""
    try:
        security_standard = SecurityStandardService.get_security_standard_by_id(db, security_standard_id)
        if not security_standard:
            logger.warning(f"Security standard with ID {security_standard_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Security standard not found"
            )
        return security_standard
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching security standard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch security standard: {str(e)}"
        )


@router.post("", response_model=SecurityStandardResponse, status_code=status.HTTP_201_CREATED)
async def create_security_standard(security_standard_data: SecurityStandardCreate, db: Session = Depends(get_db)):
    """Create a new security standard"""
    try:
        security_standard = SecurityStandardService.create_security_standard(db, security_standard_data)
        logger.info(f"Security standard created successfully: {security_standard.name}")
        return security_standard
    except ValueError as e:
        logger.error(f"Validation error creating security standard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating security standard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create security standard: {str(e)}"
        )


@router.put("/{security_standard_id}", response_model=SecurityStandardResponse)
async def update_security_standard(
    security_standard_id: int, 
    security_standard_data: SecurityStandardUpdate, 
    db: Session = Depends(get_db)
):
    """Update an existing security standard"""
    try:
        updated_security_standard = SecurityStandardService.update_security_standard(db, security_standard_id, security_standard_data)
        if not updated_security_standard:
            logger.warning(f"Security standard with ID {security_standard_id} not found for update")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Security standard not found"
            )
        logger.info(f"Security standard with ID {security_standard_id} updated successfully")
        return updated_security_standard
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating security standard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating security standard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update security standard: {str(e)}"
        )


@router.delete("/{security_standard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_security_standard(security_standard_id: int, db: Session = Depends(get_db)):
    """Delete a security standard"""
    try:
        success = SecurityStandardService.delete_security_standard(db, security_standard_id)
        if not success:
            logger.warning(f"Security standard with ID {security_standard_id} not found for deletion")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Security standard not found"
            )
        logger.info(f"Security standard with ID {security_standard_id} deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting security standard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete security standard: {str(e)}"
        )
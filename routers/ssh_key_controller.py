from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from config.config_database import get_db
from models.sshkey import SshKey

from schemas.ssh_key_schemas import SshKeyCreate, SshKeyResponse,SshKeyUpdateRequest, SshKeyUpdateResponse
from services.ssh_key_service import SshKeyService


import logging
logging.basicConfig(
    level=logging.INFO,  # Log level: DEBUG < INFO < WARNING < ERROR < CRITICAL
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ssh-keys", tags=["SSH Keys"])

"""get all ssh keys"""
@router.get("", response_model=list[SshKeyResponse])
async def get_all_ssh_keys(db: Session = Depends(get_db)):
    try:
        ssh_keys = SshKeyService.get_all_ssh_key(db)
        return ssh_keys
    except Exception as e:
        logger.error(f"Error fetching SSH keys: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch SSH keys: {str(e)}"
        )

""" get ssh key by id """
@router.get("/{ssh_key_id}", response_model=SshKeyResponse)
async def get_ssh_key(ssh_key_id: int, db: Session = Depends(get_db)):
    try:
        ssh_key = SshKeyService.get_ssh_key_by_id(db, ssh_key_id)
        if not ssh_key:
            logger.warning(f"SSH key with ID {ssh_key_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SSH key not found"
            )
        return ssh_key
    except Exception as e:
        logger.error(f"Error fetching SSH key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch SSH key: {str(e)}"
        )


""" create ssh key """
@router.post("", response_model=SshKeyResponse, status_code= status.HTTP_201_CREATED)
async def create_ssh_key(ssh_key_data : SshKeyCreate, db : Session = Depends(get_db)):
    try:
        ssh_key = SshKeyService.create_ssh_key(db, ssh_key_data)
        logger.info(f"SSH key created successfully: {ssh_key.name}")

        return ssh_key
    except ValueError as e:
        logger.error(f"Error creating SSH key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create SSH key: {str(e)}"
        )
""" delete ssh key """
@router.delete("/{ssh_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ssh_key(ssh_key_id: int, db: Session = Depends(get_db)):
    try:
        if not SshKeyService.delete_ssh_key(db, ssh_key_id):
            logger.warning(f"SSH key with ID {ssh_key_id} not found for deletion")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SSH key not found"
            )
        logger.info(f"SSH key with ID {ssh_key_id} deleted successfully")
    except Exception as e:
        logger.error(f"Error deleting SSH key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete SSH key: {str(e)}"
        )

""" update ssh key """
@router.put("/{ssh_key_id}", response_model=SshKeyUpdateResponse)
async def update_ssh_key( ssh_key_id : int, sh_key_data: SshKeyUpdateRequest, db: Session = Depends(get_db)):
    try:
        updated_ssh_key = SshKeyService.update_ssh_key(db, sh_key_data, ssh_key_id)
        logger.info(f"SSH key with ID {ssh_key_id} updated controller")
        if not updated_ssh_key:
            logger.warning(f"SSH key with ID {ssh_key_id} not found for update")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SSH key not found"
            )
        logger.info(f"SSH key with ID {ssh_key_id} updated successfully")
        return updated_ssh_key
    except Exception as e:
        logger.error(f"Error updating SSH key: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update SSH key: {str(e)}"
        )

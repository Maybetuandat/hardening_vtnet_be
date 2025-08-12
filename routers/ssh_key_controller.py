from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from config.config_database import get_db
from models.ssh_key import SshKey

from schemas.ssh_key_schemas import SshKeyCreate, SshKeyResponse
from services.ssh_key_service import SshKeyService


import logging
logging.basicConfig(
    level=logging.INFO,  # Log level: DEBUG < INFO < WARNING < ERROR < CRITICAL
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ssh-keys", tags=["SSH Keys"])
router.post("/", response_model=SshKeyResponse, status_code= status.HTTP_201_CREATED)


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

    


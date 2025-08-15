import base64
import hashlib
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
import logging
from dao.ssh_key_dao import SshKeyDao
from models import sshkey
from models.sshkey import SshKey
from schemas.ssh_key_schemas import SshKeyCreate, SshKeyResponse, SshKeyUpdateRequest, SshKeyUpdateResponse
logging.basicConfig(
    level=logging.INFO,  # Mức log: DEBUG < INFO < WARNING < ERROR < CRITICAL
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
class SshKeyService: 
   


    @staticmethod
    def get_all_ssh_key(db : Session ) -> list[SshKey]:
        try:
            logger.info("Fetching all SSH Keys from database")
            ssh_keys = SshKeyDao.get_all_ssh_keys(db)
            logger.info(f"Found {len(ssh_keys)} SSH Keys")
            return [SshKeyService._to_response(ssh_key) for ssh_key in ssh_keys]
        except Exception as e:
            logger.error(f"Error fetching SSH keys: {str(e)}")
            raise
        

    @staticmethod
    def create_ssh_key(db: Session, ssh_key_data: SshKeyCreate) -> SshKeyResponse: 
        try:
            logger.info("In create_ssh_key service method")
            
            if SshKeyDao.exists_by_name(db, ssh_key_data.name):
                raise ValueError("SSH key with this name already exists")
                
            fingerprint = SshKeyService.generate_fingerprint(ssh_key_data.public_key)
            if not fingerprint:
                raise ValueError("Failed to generate fingerprint for public key")
                
            if SshKeyDao.exists_by_fingerprint(db, fingerprint):
                raise ValueError("SSH key with this fingerprint already exists")

          
            
            ssh_key = SshKey(
                name=ssh_key_data.name,
                description=ssh_key_data.description,
                key_type=ssh_key_data.key_type,
                public_key=ssh_key_data.public_key,
                private_key=ssh_key_data.private_key,
                fingerprint=fingerprint
            )
            
            created_ssh_key = SshKeyDao.create(db, ssh_key)
            logger.info(f"SSH key created in database with ID: {created_ssh_key.id}")
            
            return SshKeyService._to_response(created_ssh_key)
            
        except Exception as e:
            logger.error(f"Error in create_ssh_key: {str(e)}")
            raise


    @staticmethod
    def get_ssh_key_by_id(db: Session, ssh_key_id: int) -> SshKeyResponse:
        try:
            logger.info(f"Fetching SSH key with ID: {ssh_key_id}")
            ssh_key = SshKeyDao.get_by_id(db, ssh_key_id)
            if not ssh_key:
                logger.warning(f"SSH key with ID {ssh_key_id} not found")
                raise HTTPException(status_code=404, detail="SSH key not found")
            return SshKeyService._to_response(ssh_key)
        except Exception as e:
            logger.error(f"Error in get_ssh_key_by_id: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to fetch SSH key")


    @staticmethod
    def delete_ssh_key(db: Session, ssh_key_id: int) -> bool:
        try:
            logger.info(f"Deleting SSH key with ID: {ssh_key_id}")
            exist_ssh_key = SshKeyDao.get_by_id(db, ssh_key_id)
            if not exist_ssh_key:
                logger.warning(f"SSH key with ID {ssh_key_id} not found for deletion")
                raise HTTPException(status_code=404, detail="SSH key not found")
            result = SshKeyDao.delete(db, exist_ssh_key)
            if result:
                logger.info(f"SSH key with ID {ssh_key_id} deleted successfully")
            else:
                logger.warning(f"SSH key with ID {ssh_key_id} not found or could not be deleted")
            return result
        except Exception as e:
            logger.error(f"Error in delete_ssh_key: {str(e)}")
            return False
    
    @staticmethod
    def update_ssh_key(db: Session, ssh_key_data: SshKeyUpdateRequest, ssh_key_id: int) -> Optional[SshKeyUpdateResponse]:
        try:
            logger.info(f"Updating SSH key with ID: {ssh_key_id}")
            exist_ssh_key = SshKeyDao.get_by_id(db, ssh_key_id)
            if not exist_ssh_key:
                logger.warning(f"SSH key with ID {ssh_key_id} not found for update ssh_key_service")
                raise HTTPException(status_code=404, detail="SSH key not found")
            if ssh_key_data.name is not None:
                exist_ssh_key.name = ssh_key_data.name
            if ssh_key_data.description is not None:
                exist_ssh_key.description = ssh_key_data.description
            if ssh_key_data.key_type is not None:
                exist_ssh_key.key_type = ssh_key_data.key_type
            if ssh_key_data.public_key is not None:
                exist_ssh_key.public_key = ssh_key_data.public_key
            
            if ssh_key_data.is_active is not None:
                exist_ssh_key.is_active = ssh_key_data.is_active
            updated_ssh_key = SshKeyDao.update(db, exist_ssh_key)
            # logger.info(f"SSH key with ID {ssh_key} updated successfully")
            return SshKeyUpdateResponse.model_validate(updated_ssh_key)
        except Exception as e:
            logger.error(f"Error in update_ssh_key: {str(e)}")
            return None
    @staticmethod
    def _to_response(ssh_key: SshKey) -> SshKeyResponse:
        return SshKeyResponse(
            id=ssh_key.id,
            name=ssh_key.name,
            description=ssh_key.description,
            key_type=ssh_key.key_type,
            public_key=ssh_key.public_key,
            fingerprint=ssh_key.fingerprint,
            is_active=ssh_key.is_active,
            created_at=ssh_key.created_at,
            updated_at=ssh_key.updated_at
        )
    @staticmethod
    def generate_fingerprint(public_key : str) -> str:
        """Generates a fingerprint for the given public key."""
        try:
            parts = public_key.strip().split()
            if len(parts) >= 2:
                key_data = parts[1]
                key_bytes = base64.b64decode(key_data)
                fingerprint = hashlib.md5(key_bytes).hexdigest()
                return ':'.join(fingerprint[i:i+2] for i in range(0, len(fingerprint), 2))
            else:
                raise ValueError("Invalid public key format")
        except  Exception as e:
            print(f"Error generating fingerprint: {e}")
            return ""
        
  
        
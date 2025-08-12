import base64
import hashlib
from sqlalchemy.orm import Session
import logging
from dao.ssh_key_dao import SshKeyDao
from models import ssh_key
from schemas.ssh_key_schemas import SSHKeyCreate, SshKeyResponse
logging.basicConfig(
    level=logging.INFO,  # Mức log: DEBUG < INFO < WARNING < ERROR < CRITICAL
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
class SshKeyService: 
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
        
    @staticmethod
    def validate_key_pair_match(public_key: str, private_key: str) -> bool:
        try:
            # Extract key type from public key
            public_key_type = public_key.split()[0]
            
            # Check if private key contains corresponding type
            if public_key_type == "ssh-rsa" and "RSA" not in private_key:
                return False
            elif public_key_type == "ssh-ed25519" and "OPENSSH" not in private_key:
                return False
            elif public_key_type.startswith("ecdsa-") and "EC" not in private_key:
                return False
            elif public_key_type == "ssh-dss" and "DSA" not in private_key:
                return False
            
            return True
        except Exception:
            return False
        
    @staticmethod
    def create_ssh_key(db : Session, ssh_key_data: SSHKeyCreate) -> ssh_key: 

        logger.info("In create_ssh_key service method")
        if SshKeyDao.exists_by_name(db, ssh_key_data.name):
            raise ValueError("SSH key with this name already exists")
        fingerprint = SshKeyService.generate_fingerprint(ssh_key_data.public_key)
        if SshKeyDao.exists_by_fingerprint(db, fingerprint):
            raise ValueError("SSH key with this fingerprint already exists")

        if not SshKeyService.validate_key_pair_match(ssh_key_data.public_key, ssh_key_data.private_key):
            raise ValueError("Public and private keys do not match")
        ssh_key = ssh_key(
            name=ssh_key_data.name,
            description=ssh_key_data.description,
            key_type=ssh_key_data.key_type,
            public_key=ssh_key_data.public_key,
            private_key=ssh_key_data.private_key,
            fingerprint=fingerprint
        )
        ssh_key = SshKeyDao.create(db, ssh_key)

        return SshKeyService._to_response(ssh_key)

    @staticmethod
    def _to_response(ssh_key : ssh_key.SshKey) -> SshKeyResponse:
        return SshKeyResponse(
            id=ssh_key.id,
            name=ssh_key.name,
            description=ssh_key.description,
            key_type=ssh_key.key_type,
            public_key=ssh_key.public_key,
            private_key=None, 
            fingerprint=ssh_key.fingerprint
        )
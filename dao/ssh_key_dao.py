
from typing import Optional
from sqlalchemy.orm import Session

from models.sshkey import SshKey


class SshKeyDao:
    @staticmethod
    def get_all_ssh_keys(db : Session) -> list[SshKey]:
        try:
            return db.query(SshKey).all()
        except Exception as e:
            print(f"Error fetching SSH keys: {e}")
            return []
    @staticmethod
    def create(db : Session, ssh_key : SshKey) -> SshKey:
        try:
            db.add(ssh_key)
            db.commit()
            db.refresh(ssh_key)
            return ssh_key
        except Exception as e:
            db.rollback()
            print(f"Error creating SSH key: {e}")
            return None
    @staticmethod
    def get_by_id(db: Session, ssh_key_id: int) -> Optional[SshKey]:
        try:
            return db.query(SshKey).filter(SshKey.id == ssh_key_id).first()
        except Exception as e:
            print(f"Error fetching SSH key by ID {ssh_key_id}: {e}")
            return None
    @staticmethod
    def delete(db: Session, ssh_key: SshKey) -> bool:
        try:
            db.delete(ssh_key)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Error deleting SSH key: {e}")
            return False

    @staticmethod
    def update(db : Session, ssh_key : SshKey) -> Optional[SshKey]:
       try:
           db.commit()
           db.refresh(ssh_key)
           return ssh_key
       except Exception as e:
           db.rollback()
           print(f"Error updating SSH key: {e}")
           return None

    @staticmethod
    def exists_by_name(db : Session, name : str) -> bool:
        """Check if an SSH key with the given name exists."""
        try:
            return db.query(SshKey).filter(SshKey.name == name).count() > 0
        except Exception as e:
            print(f"Error checking existence of SSH key by name {name}: {e}")
            return False

    @staticmethod
    def exists_by_fingerprint(db : Session, fingerprint : str) -> bool:
        try:
            return db.query(SshKey).filter(SshKey.fingerprint == fingerprint).count() > 0
        except Exception as e:
            print(f"Error checking existence of SSH key by fingerprint {fingerprint}: {e}")
            return False

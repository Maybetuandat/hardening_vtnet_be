
from typing import Optional
from sqlalchemy.orm import Session

from models.ssh_key import SshKey


class SshKeyDao:
    @staticmethod
    def create(db : Session, ssh_key : SshKey) -> SshKey:
        db.add(ssh_key)
        db.commit()
        db.refresh(ssh_key)
        return ssh_key
    @staticmethod
    def get_by_id(db: Session, ssh_key_id: int) -> Optional[SshKey]:
        return db.query(SshKey).filter(SshKey.id == ssh_key_id).first()

    @staticmethod
    def delete(db: Session, ssh_key_id : int) -> bool:
        ssh_key = db.query(SshKey).filter(SshKey.id == ssh_key_id).first()
        if ssh_key:
            try:
                db.delete(ssh_key)
                db.commit()
                return True
            except Exception as e:
                db.rollback()
                print(f"Error deleting SSH key: {e}")
                return False
        return False
    @staticmethod
    def exists_by_name(db : Session, name : str) -> bool:
        return db.query(SshKey).filter(SshKey.name == name).count() > 0

    @staticmethod
    def exists_by_fingerprint(db : Session, fingerprint : str) -> bool:
        return db.query(SshKey).filter(SshKey.fingerprint == fingerprint).count() > 0

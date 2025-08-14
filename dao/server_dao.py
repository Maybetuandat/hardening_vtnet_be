from typing import List, Optional
from sqlalchemy.orm import Session
from models.server import Server
from schemas.server_schemas import ServerCreate, ServerUpdate


class ServerDao:
    """Data Access Object for Server operations"""

    @staticmethod
    def get_all_servers(db: Session) -> List[Server]:
        """Get all servers"""
        return db.query(Server).all()

    @staticmethod
    def get_server_by_id(db: Session, server_id: int) -> Optional[Server]:
        """Get server by ID"""
        return db.query(Server).filter(Server.id == server_id).first()

    @staticmethod
    def get_server_by_hostname(db: Session, hostname: str) -> Optional[Server]:
        """Get server by hostname"""
        return db.query(Server).filter(Server.hostname == hostname).first()

    @staticmethod
    def get_server_by_ip(db: Session, ip_address: str) -> Optional[Server]:
        """Get server by IP address"""
        return db.query(Server).filter(Server.ip_address == ip_address).first()

    @staticmethod
    def exists_by_hostname(db: Session, hostname: str) -> bool:
        """Check if server exists by hostname"""
        return db.query(Server).filter(Server.hostname == hostname).first() is not None

    @staticmethod
    def exists_by_hostname_exclude_id(db: Session, hostname: str, server_id: int) -> bool:
        """Check if server exists by hostname excluding specific ID"""
        return db.query(Server).filter(
            Server.hostname == hostname,
            Server.id != server_id
        ).first() is not None

    @staticmethod
    def exists_by_ip(db: Session, ip_address: str) -> bool:
        """Check if server exists by IP address"""
        return db.query(Server).filter(Server.ip_address == ip_address).first() is not None

    @staticmethod
    def exists_by_ip_exclude_id(db: Session, ip_address: str, server_id: int) -> bool:
        """Check if server exists by IP address excluding specific ID"""
        return db.query(Server).filter(
            Server.ip_address == ip_address,
            Server.id != server_id
        ).first() is not None

    @staticmethod
    def create_server(db: Session, server_data: ServerCreate) -> Server:
        """Create a new server"""
        db_server = Server(
            name=server_data.name,
            hostname=server_data.hostname,
            ip_address=server_data.ip_address,
            workload_id=server_data.workload_id,
            server_role=server_data.server_role,
            os_type=server_data.os_type,
            os_name=server_data.os_name,
            os_version=server_data.os_version,
            cpu_cores=server_data.cpu_cores,
            memory_gb=server_data.memory_gb,
            environment=server_data.environment,
            status=server_data.status,
          
            ssh_port=server_data.ssh_port,
            ssh_key_id=server_data.ssh_key_id,
            is_active=server_data.is_active
        )
        db.add(db_server)
        db.commit()
        db.refresh(db_server)
        return db_server

    @staticmethod
    def update_server(db: Session, server_id: int, server_data: ServerUpdate) -> Optional[Server]:
        """Update an existing server"""
        db_server = db.query(Server).filter(Server.id == server_id).first()
        if not db_server:
            return None

        # Update only provided fields
        update_data = server_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_server, field, value)

        db.commit()
        db.refresh(db_server)
        return db_server

    @staticmethod
    def delete_server(db: Session, server_id: int) -> bool:
        """Delete a server"""
        db_server = db.query(Server).filter(Server.id == server_id).first()
        if not db_server:
            return False

        db.delete(db_server)
        db.commit()
        return True

    @staticmethod
    def get_servers_by_workload(db: Session, workload_id: int) -> List[Server]:
        """Get servers by workload ID"""
        return db.query(Server).filter(Server.workload_id == workload_id).all()

    @staticmethod
    def get_servers_by_environment(db: Session, environment: str) -> List[Server]:
        """Get servers by environment"""
        return db.query(Server).filter(Server.environment == environment).all()

    @staticmethod
    def get_servers_by_os_type(db: Session, os_type: str) -> List[Server]:
        """Get servers by OS type"""
        return db.query(Server).filter(Server.os_type == os_type).all()

    @staticmethod
    def get_servers_by_status(db: Session, status: str) -> List[Server]:
        """Get servers by status"""
        return db.query(Server).filter(Server.status == status).all()

    @staticmethod
    def get_active_servers(db: Session) -> List[Server]:
        """Get only active servers"""
        return db.query(Server).filter(Server.is_active == True).all()

    @staticmethod
    def get_servers_by_ssh_key(db: Session, ssh_key_id: int) -> List[Server]:
        """Get servers using specific SSH key"""
        return db.query(Server).filter(Server.ssh_key_id == ssh_key_id).all()

    @staticmethod
    def get_server_count_by_workload(db: Session, workload_id: int) -> int:
        """Get count of servers in a workload"""
        return db.query(Server).filter(Server.workload_id == workload_id).count()
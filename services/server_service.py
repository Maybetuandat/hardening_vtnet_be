from typing import List, Optional
from sqlalchemy.orm import Session
import logging

from dao.server_dao import ServerDao
from dao.workload_dao import WorkloadDao
from dao.ssh_key_dao import SshKeyDao
from models.server import Server
from schemas.server_schemas import ServerCreate, ServerUpdate, ServerResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class ServerService:
    """Service layer for Server operations"""

    @staticmethod
    def get_all_servers(db: Session) -> List[ServerResponse]:
        """Get all servers"""
        try:
            logger.info("Fetching all servers from database")
            servers = ServerDao.get_all_servers(db)
            logger.info(f"Found {len(servers)} servers")
            return [ServerService._to_response(server) for server in servers]
        except Exception as e:
            logger.error(f"Error fetching servers: {str(e)}")
            raise

    @staticmethod
    def get_server_by_id(db: Session, server_id: int) -> Optional[ServerResponse]:
        """Get server by ID"""
        try:
            logger.info(f"Fetching server with ID: {server_id}")
            server = ServerDao.get_server_by_id(db, server_id)
            if server:
                logger.info(f"Found server: {server.name}")
                return ServerService._to_response(server)
            else:
                logger.warning(f"Server with ID {server_id} not found")
                return None
        except Exception as e:
            logger.error(f"Error fetching server: {str(e)}")
            raise

    @staticmethod
    def create_server(db: Session, server_data: ServerCreate) -> ServerResponse:
        """Create a new server"""
        try:
            logger.info(f"Creating new server: {server_data.name}")
            
            # Validate workload exists
            if not WorkloadDao.get_workload_by_id(db, server_data.workload_id):
                raise ValueError(f"Workload with ID {server_data.workload_id} does not exist")
            
            # Validate SSH key exists (if provided)
            if server_data.ssh_key_id:
                if not SshKeyDao.get_by_id(db, server_data.ssh_key_id):
                    raise ValueError(f"SSH Key with ID {server_data.ssh_key_id} does not exist")
            
            # Check if server with same hostname already exists
            if ServerDao.exists_by_hostname(db, server_data.hostname):
                raise ValueError(f"Server with hostname '{server_data.hostname}' already exists")
            
            # Check if server with same IP already exists
            if ServerDao.exists_by_ip(db, server_data.ip_address):
                raise ValueError(f"Server with IP address '{server_data.ip_address}' already exists")
            
            server = ServerDao.create_server(db, server_data)
            logger.info(f"Server created successfully: {server.name}")
            return ServerService._to_response(server)
        except ValueError as e:
            logger.error(f"Validation error creating server: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating server: {str(e)}")
            raise

    @staticmethod
    def update_server(db: Session, server_id: int, server_data: ServerUpdate) -> Optional[ServerResponse]:
        """Update an existing server"""
        try:
            logger.info(f"Updating server with ID: {server_id}")
            
            # Check if server exists
            existing_server = ServerDao.get_server_by_id(db, server_id)
            if not existing_server:
                logger.warning(f"Server with ID {server_id} not found for update")
                return None
            
            # Validate workload exists (if being updated)
            if server_data.workload_id:
                if not WorkloadDao.get_workload_by_id(db, server_data.workload_id):
                    raise ValueError(f"Workload with ID {server_data.workload_id} does not exist")
            
            # Validate SSH key exists (if being updated)
            if server_data.ssh_key_id:
                if not SshKeyDao.get_ssh_key_by_id(db, server_data.ssh_key_id):
                    raise ValueError(f"SSH Key with ID {server_data.ssh_key_id} does not exist")
            
            # Check if new hostname conflicts with existing server (if hostname is being updated)
            if server_data.hostname and server_data.hostname != existing_server.hostname:
                if ServerDao.exists_by_hostname_exclude_id(db, server_data.hostname, server_id):
                    raise ValueError(f"Server with hostname '{server_data.hostname}' already exists")
            
            # Check if new IP conflicts with existing server (if IP is being updated)
            if server_data.ip_address and server_data.ip_address != existing_server.ip_address:
                if ServerDao.exists_by_ip_exclude_id(db, server_data.ip_address, server_id):
                    raise ValueError(f"Server with IP address '{server_data.ip_address}' already exists")
            
            updated_server = ServerDao.update_server(db, server_id, server_data)
            if updated_server:
                logger.info(f"Server updated successfully: {updated_server.name}")
                return ServerService._to_response(updated_server)
            return None
        except ValueError as e:
            logger.error(f"Validation error updating server: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error updating server: {str(e)}")
            raise

    @staticmethod
    def delete_server(db: Session, server_id: int) -> bool:
        """Delete a server"""
        try:
            logger.info(f"Deleting server with ID: {server_id}")
            
            # Check if server exists
            existing_server = ServerDao.get_server_by_id(db, server_id)
            if not existing_server:
                logger.warning(f"Server with ID {server_id} not found for deletion")
                return False
            
            success = ServerDao.delete_server(db, server_id)
            if success:
                logger.info(f"Server with ID {server_id} deleted successfully")
            return success
        except Exception as e:
            logger.error(f"Error deleting server: {str(e)}")
            raise

    @staticmethod
    def get_servers_by_workload(db: Session, workload_id: int) -> List[ServerResponse]:
        """Get servers by workload ID"""
        try:
            logger.info(f"Fetching servers for workload: {workload_id}")
            servers = ServerDao.get_servers_by_workload(db, workload_id)
            logger.info(f"Found {len(servers)} servers for workload {workload_id}")
            return [ServerService._to_response(server) for server in servers]
        except Exception as e:
            logger.error(f"Error fetching servers by workload: {str(e)}")
            raise

    @staticmethod
    def get_servers_by_environment(db: Session, environment: str) -> List[ServerResponse]:
        """Get servers by environment"""
        try:
            logger.info(f"Fetching servers for environment: {environment}")
            servers = ServerDao.get_servers_by_environment(db, environment)
            logger.info(f"Found {len(servers)} servers for environment {environment}")
            return [ServerService._to_response(server) for server in servers]
        except Exception as e:
            logger.error(f"Error fetching servers by environment: {str(e)}")
            raise

    @staticmethod
    def get_servers_by_os_type(db: Session, os_type: str) -> List[ServerResponse]:
        """Get servers by OS type"""
        try:
            logger.info(f"Fetching servers for OS type: {os_type}")
            servers = ServerDao.get_servers_by_os_type(db, os_type)
            logger.info(f"Found {len(servers)} servers for OS type {os_type}")
            return [ServerService._to_response(server) for server in servers]
        except Exception as e:
            logger.error(f"Error fetching servers by OS type: {str(e)}")
            raise

    @staticmethod
    def get_servers_by_status(db: Session, status: str) -> List[ServerResponse]:
        """Get servers by status"""
        try:
            logger.info(f"Fetching servers with status: {status}")
            servers = ServerDao.get_servers_by_status(db, status)
            logger.info(f"Found {len(servers)} servers with status {status}")
            return [ServerService._to_response(server) for server in servers]
        except Exception as e:
            logger.error(f"Error fetching servers by status: {str(e)}")
            raise

    @staticmethod
    def get_active_servers(db: Session) -> List[ServerResponse]:
        """Get only active servers"""
        try:
            logger.info("Fetching active servers")
            servers = ServerDao.get_active_servers(db)
            logger.info(f"Found {len(servers)} active servers")
            return [ServerService._to_response(server) for server in servers]
        except Exception as e:
            logger.error(f"Error fetching active servers: {str(e)}")
            raise

    @staticmethod
    def _to_response(server: Server) -> ServerResponse:
        """Convert Server model to ServerResponse"""
        return ServerResponse(
            id=server.id,
            name=server.name,
            hostname=server.hostname,
            ip_address=server.ip_address,
            workload_id=server.workload_id,
            server_role=server.server_role,
            os_type=server.os_type,
            os_name=server.os_name,
            os_version=server.os_version,
            cpu_cores=server.cpu_cores,
            memory_gb=server.memory_gb,
            environment=server.environment,
            status=server.status,
            compliance_score=server.compliance_score,
            ssh_port=server.ssh_port,
            ssh_key_id=server.ssh_key_id,
            is_active=server.is_active,
            created_at=server.created_at,
            updated_at=server.updated_at
        )
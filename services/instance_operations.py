"""
File 4: instance_operations.py
Service for instance CRUD operations
Reusable methods for add/update/delete/check operations
"""
import logging
from typing import Any, Dict, List, Tuple
from sqlalchemy.orm import Session

from models.instance import Instance
from models.os import Os

logger = logging.getLogger(__name__)


class InstanceOperations:
    """Service for instance CRUD operations"""

    def __init__(self, db: Session):
        self.db = db

    def check_instance_needs_update(
        self,
        dcim_inst: Dict[str, Any],
        backend_inst: Dict[str, Any],
        os_dao: Any,
        user_dao: Any
    ) -> Tuple[bool, List[str]]:
        """
        Check if instance needs update
        Compare OS name and User username instead of IDs
        
        Args:
            dcim_inst: Instance data from DCIM
            backend_inst: Instance data from Backend
            os_dao: OS DAO for database operations
            user_dao: User DAO for database operations
            
        Returns:
            Tuple: (needs_update: bool, changes: List[str])
        """
        changes = []
        
        try:
            # Compare OS
            dcim_os_name = dcim_inst.get("os", {}).get("name")
            if dcim_os_name:
                backend_os_id = backend_inst.get("os_id")
                backend_os = None
                if backend_os_id:
                    backend_os = os_dao.get_by_id(backend_os_id)
                
                backend_os_name = backend_os.name if backend_os else None
                
                if dcim_os_name != backend_os_name:
                    changes.append(f"OS: {backend_os_name} → {dcim_os_name}")
            
            # Compare User/Manager
            dcim_username = dcim_inst.get("manager", {}).get("username")
            if dcim_username:
                backend_user_id = backend_inst.get("user_id")
                backend_user = None
                if backend_user_id:
                    backend_user = user_dao.get_by_id(backend_user_id)
                
                backend_username = backend_user.username if backend_user else None
                
                if dcim_username != backend_username:
                    changes.append(f"User: {backend_username} → {dcim_username}")
            
            needs_update = len(changes) > 0
            
            return needs_update, changes
            
        except Exception as e:
            logger.error(f"Error checking instance updates: {e}")
            return True, ["Error checking, will attempt update"]

    def add_instance_to_backend(
        self,
        dcim_inst: Dict[str, Any],
        instance_dao: Any,
        os_dao: Any,
        user_dao: Any
    ) -> Dict[str, Any]:
        """
        Add new instance to backend from DCIM data
        Auto-create OS if not exists
        
        Args:
            dcim_inst: Instance data from DCIM
            instance_dao: Instance DAO for database operations
            os_dao: OS DAO for database operations
            user_dao: User DAO for database operations
            
        Returns:
            Dict with success status and created instance info
        """
        try:
            ip = dcim_inst.get("name")
            os_info = dcim_inst.get("os", {})
            manager_info = dcim_inst.get("manager", {})
            instance_role = dcim_inst.get("instance_role", {})
            
            # STEP 1: Handle OS - Find or create
            os_name = os_info.get("name")
            os_record = None
            
            if os_name:
                os_record = os_dao.get_by_name(os_name)
                
                if not os_record:
                    print(f"   📦 OS '{os_name}' not found → Creating new OS...")
                    
                    os_data = {
                        "name": os_name,
                        "type": os_info.get("type", 1),
                        "display": os_info.get("display", os_name)
                    }

                    os_record = os_dao.create(Os(**os_data))
                    print(f"   ✅ Created OS: {os_name} (ID: {os_record.id})")
                else:
                    print(f"   ✅ OS '{os_name}' found (ID: {os_record.id})")
            else:
                print(f"   ⚠️ No OS info in DCIM, skipping OS assignment")
            
            # STEP 2: Handle User - Find or return error
            username = manager_info.get("username")
            
            if not username:
                return {
                    "success": False,
                    "error": "No username found in DCIM manager info"
                }
            
            user_record = user_dao.get_by_username(username)
            
            if not user_record:
                return {
                    "success": False,
                    "error": f"User '{username}' not found in backend"
                }
            
            # STEP 3: Create new instance
            new_instance_data = {
                "name": ip,
                "os_id": os_record.id if os_record else None,
                "user_id": user_record.id,
                "status": True,
                "ssh_port": 22,
                "workload_id": None,
                "instance_role": instance_role.get("name") if instance_role else None
            }
            
            new_instance = instance_dao.create(Instance(**new_instance_data))
            print(f"   ✅ Created Instance: {ip} (ID: {new_instance.id})")
            
            return {
                "success": True,
                "backend_id": new_instance.id,
                "user_manage": user_record.username,
                "created_os": os_record.name if os_record else None
            }
            
        except Exception as e:
            logger.error(f"❌ Error adding instance: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }

    def update_instance_in_backend(
        self,
        dcim_inst: Dict[str, Any],
        backend_inst: Dict[str, Any],
        instance_dao: Any,
        os_dao: Any,
        user_dao: Any
    ) -> Dict[str, Any]:
        """
        Update instance in Backend with DCIM data
        Automatically create OS if not exists
        
        Args:
            dcim_inst: Instance data from DCIM
            backend_inst: Instance data from Backend
            instance_dao: Instance DAO for database operations
            os_dao: OS DAO for database operations
            user_dao: User DAO for database operations
            
        Returns:
            Dict: {"success": bool, "error": str, "changes": List[str]}
        """
        try:
            backend_id = backend_inst.get("id")
            update_data = {}
            
            # STEP 1: Handle OS - Find or create
            os_info = dcim_inst.get("os", {})
            os_name = os_info.get("name")
            
            if os_name:
                os_record = os_dao.get_by_name(os_name)
                
                if not os_record:
                    print(f"   📦 OS '{os_name}' not found → Creating new OS...")
                    
                    os_data = {
                        "name": os_name,
                        "type": os_info.get("type", 1),
                        "display": os_info.get("display", os_name)
                    }
                    
                    os_record = os_dao.create(Os(**os_data))
                    print(f"   ✅ Created OS: {os_name} (ID: {os_record.id})")
                
                if os_record and backend_inst.get("os_id") != os_record.id:
                    update_data["os_id"] = os_record.id
                    print(f"   🔄 OS will be updated: {os_record.name}")
            
            # STEP 2: Handle User - Find only
            manager_info = dcim_inst.get("manager", {})
            username = manager_info.get("username")
            
            if username:
                user_record = user_dao.get_by_username(username)
                if user_record and backend_inst.get("user_id") != user_record.id:
                    update_data["user_id"] = user_record.id
                    print(f"   🔄 User will be updated: {user_record.username}")
            
            # STEP 3: Perform update if changes exist
            if update_data:
                instance_dao.update(backend_id, update_data)
                print(f"   ✅ Updated instance with changes: {list(update_data.keys())}")
                return {
                    "success": True,
                    "changes": list(update_data.keys())
                }
            else:
                return {
                    "success": True,
                    "note": "No changes needed"
                }
            
        except Exception as e:
            logger.error(f"❌ Error updating instance: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }

    def delete_instance_from_backend(
        self,
        backend_inst: Dict[str, Any],
        instance_dao: Any
    ) -> Dict[str, Any]:
        """
        Delete instance from backend
        
        Args:
            backend_inst: Instance data from Backend
            instance_dao: Instance DAO for database operations
            
        Returns:
            Dict with success status
        """
        try:
            backend_id = backend_inst.get("id")
            instance_delete = instance_dao.get_by_id(backend_id)
            if not instance_delete:
                return {
                    "success": False,
                    "error": "Instance not found in backend"
                }   
            
            instance_dao.delete(instance_delete)
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Error deleting instance: {e}")
            return {
                "success": False,
                "error": str(e)
            }
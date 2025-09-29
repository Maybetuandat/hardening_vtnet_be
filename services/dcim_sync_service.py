"""
File 3: dcim_sync_service.py
Service for syncing instances between DCIM and Backend
Handles both bulk import and incremental sync
"""
import logging
from typing import Any, Dict, List
from sqlalchemy.orm import Session

from dao.instance_dao import InstanceDAO
from dao.os_dao import OsDao
from dao.user_dao import UserDAO
from services.backend_cache_service import BackendCacheService
from services.instance_operations import InstanceOperations

logger = logging.getLogger(__name__)


class DCIMSyncService:
    """Service for syncing instances between DCIM and Backend"""

    def __init__(self, db: Session):
        self.db = db
        self.backend_cache_service = BackendCacheService(db)
        self.instance_ops = InstanceOperations(db)

    def bulk_import_from_dcim(
        self,
        dcim_instances: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Initial bulk import when backend cache is empty
        Adds all DCIM instances to backend without checking for updates/deletes
        
        Args:
            dcim_instances: List of instances from DCIM
            
        Returns:
            Dict with success status and statistics
        """
        try:
            print("\n" + "="*60)
            print("📦 BULK IMPORT: Adding all instances from DCIM to Backend")
            print("="*60)
            
            instance_dao = InstanceDAO(self.db)
            os_dao = OsDao(self.db)
            user_dao = UserDAO(self.db)
            
            stats = {
                "added": [],
                "errors": []
            }
            
            print(f"\n📋 Processing {len(dcim_instances)} instances from DCIM...")
            
            for dcim_inst in dcim_instances:
                try:
                    dcim_ip = dcim_inst.get("name")
                    
                    if not dcim_ip:
                        logger.warning(f"⚠️ DCIM instance has no IP, skipping...")
                        continue
                    
                    print(f"\n➕ [{dcim_ip}] Adding to Backend...")
                    
                    result = self.instance_ops.add_instance_to_backend(
                        dcim_inst, 
                        instance_dao, 
                        os_dao, 
                        user_dao
                    )
                    
                    if result["success"]:
                        stats["added"].append({
                            "ip": dcim_ip,
                            "backend_id": result.get("backend_id")
                        })
                        print(f"   ✅ Added successfully (Backend ID: {result.get('backend_id')})")
                    else:
                        stats["errors"].append({
                            "ip": dcim_ip,
                            "action": "add",
                            "error": result.get("error")
                        })
                        print(f"   ❌ Failed to add: {result.get('error')}")
                
                except Exception as e:
                    logger.error(f"❌ Error processing DCIM instance {dcim_inst.get('name')}: {e}")
                    stats["errors"].append({
                        "ip": dcim_inst.get("name"),
                        "action": "process",
                        "error": str(e)
                    })
            
            # Commit all changes
            try:
                self.db.commit()
                print("\n💾 All changes committed to database")
            except Exception as e:
                self.db.rollback()
                logger.error(f"❌ Failed to commit changes: {e}")
                return {
                    "success": False,
                    "error": f"Database commit failed: {str(e)}"
                }
            
            # Print summary
            print("\n" + "="*60)
            print("✅ BULK IMPORT COMPLETED")
            print("="*60)
            print(f"📊 Summary:")
            print(f"   ➕ Added:     {len(stats['added'])} instances")
            print(f"   ⚠️ Errors:    {len(stats['errors'])} instances")
            print("="*60 + "\n")
            
            # Refresh backend cache
            print("🔄 Refreshing backend cache...")
            self.backend_cache_service.refresh_cache()
            
            return {
                "success": True,
                "stats": stats,
                "summary": {
                    "total_dcim": len(dcim_instances),
                    "added": len(stats["added"]),
                    "errors": len(stats["errors"])
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error in bulk_import_from_dcim: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            try:
                self.db.rollback()
            except:
                pass
            
            return {
                "success": False,
                "error": str(e)
            }

    def sync_instances_between_dcim_and_backend(
        self,
        dcim_instances: List[Dict[str, Any]],
        backend_instances: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Normal sync operation between DCIM and Backend
        Handles add/update/delete operations
        
        Args:
            dcim_instances: List of instances from DCIM
            backend_instances: List of instances from Backend
            
        Returns:
            Dict with success status and detailed statistics
        """
        try:
            instance_dao = InstanceDAO(self.db)
            os_dao = OsDao(self.db)
            user_dao = UserDAO(self.db)
            
            print("\n" + "="*60)
            print("🔄 STARTING SYNC: DCIM → Backend")
            print("="*60)
            
            stats = {
                "added": [],
                "updated": [],
                "deleted": [],
                "unchanged": [],
                "errors": []
            }
            
            backend_dict = {inst["name"]: inst for inst in backend_instances}
            processed_dcim_ips = set()
            
            # STEP 1: Process DCIM instances
            print(f"\n📋 Processing {len(dcim_instances)} instances from DCIM...")
            
            for dcim_inst in dcim_instances:
                try:
                    dcim_ip = dcim_inst.get("name")
                    
                    if not dcim_ip:
                        logger.warning(f"⚠️ DCIM instance has no IP, skipping...")
                        continue
                    
                    processed_dcim_ips.add(dcim_ip)
                    backend_inst = backend_dict.get(dcim_ip)
                    
                    # CASE 1: Not in backend -> ADD
                    if backend_inst is None:
                        print(f"\n➕ [{dcim_ip}] Found in DCIM but NOT in Backend → Adding...")
                        
                        result = self.instance_ops.add_instance_to_backend(
                            dcim_inst, 
                            instance_dao, 
                            os_dao, 
                            user_dao
                        )
                        
                        if result["success"]:
                            stats["added"].append({
                                "ip": dcim_ip,
                                "backend_id": result.get("backend_id")
                            })
                            print(f"   ✅ Added successfully (Backend ID: {result.get('backend_id')})")
                        else:
                            stats["errors"].append({
                                "ip": dcim_ip,
                                "action": "add",
                                "error": result.get("error")
                            })
                            print(f"   ❌ Failed to add: {result.get('error')}")
                    
                    # CASE 2: In both -> CHECK and UPDATE
                    else:
                        print(f"\n🔄 [{dcim_ip}] Found in BOTH → Checking for changes...")
                        
                        needs_update, changes = self.instance_ops.check_instance_needs_update(
                            dcim_inst, 
                            backend_inst,
                            os_dao,
                            user_dao
                        )
                        
                        if needs_update:
                            print(f"   📝 Changes detected: {changes}")
                            
                            result = self.instance_ops.update_instance_in_backend(
                                dcim_inst,
                                backend_inst,
                                instance_dao,
                                os_dao,
                                user_dao
                            )
                            
                            if result["success"]:
                                stats["updated"].append({
                                    "ip": dcim_ip,
                                    "backend_id": backend_inst["id"],
                                    "changes": changes
                                })
                                print(f"   ✅ Updated successfully")
                            else:
                                stats["errors"].append({
                                    "ip": dcim_ip,
                                    "action": "update",
                                    "error": result.get("error")
                                })
                                print(f"   ❌ Failed to update: {result.get('error')}")
                        else:
                            stats["unchanged"].append({
                                "ip": dcim_ip,
                                "backend_id": backend_inst["id"]
                            })
                            print(f"   ℹ️ No changes needed")
                
                except Exception as e:
                    logger.error(f"❌ Error processing DCIM instance {dcim_inst.get('name')}: {e}")
                    stats["errors"].append({
                        "ip": dcim_inst.get("name"),
                        "action": "process",
                        "error": str(e)
                    })
            
            # STEP 2: Delete instances not in DCIM
            print(f"\n🗑️ Checking for instances to delete from Backend...")
            
            for backend_inst in backend_instances:
                backend_ip = backend_inst.get("name")
                backend_id = backend_inst.get("id")
                
                if backend_ip not in processed_dcim_ips:
                    print(f"\n❌ [{backend_ip}] NOT found in DCIM → Deleting from Backend...")
                    
                    result = self.instance_ops.delete_instance_from_backend(
                        backend_inst,
                        instance_dao
                    )
                    
                    if result["success"]:
                        stats["deleted"].append({
                            "ip": backend_ip,
                            "backend_id": backend_id
                        })
                        print(f"   ✅ Deleted successfully")
                    else:
                        stats["errors"].append({
                            "ip": backend_ip,
                            "action": "delete",
                            "error": result.get("error")
                        })
                        print(f"   ❌ Failed to delete: {result.get('error')}")
            
            # Commit changes
            try:
                self.db.commit()
                print("\n💾 All changes committed to database")
            except Exception as e:
                self.db.rollback()
                logger.error(f"❌ Failed to commit changes: {e}")
                return {
                    "success": False,
                    "error": f"Database commit failed: {str(e)}"
                }
            
            # Print summary
            print("\n" + "="*60)
            print("✅ SYNC COMPLETED")
            print("="*60)
            print(f"📊 Summary:")
            print(f"   ➕ Added:     {len(stats['added'])} instances")
            print(f"   🔄 Updated:   {len(stats['updated'])} instances")
            print(f"   ❌ Deleted:   {len(stats['deleted'])} instances")
            print(f"   ℹ️ Unchanged: {len(stats['unchanged'])} instances")
            print(f"   ⚠️ Errors:    {len(stats['errors'])} instances")
            print("="*60 + "\n")
            
            # Refresh backend cache
            print("🔄 Refreshing backend cache...")
            self.backend_cache_service.refresh_cache()
            
            return {
                "success": True,
                "stats": stats,
                "summary": {
                    "total_dcim": len(dcim_instances),
                    "total_backend_before": len(backend_instances),
                    "added": len(stats["added"]),
                    "updated": len(stats["updated"]),
                    "deleted": len(stats["deleted"]),
                    "unchanged": len(stats["unchanged"]),
                    "errors": len(stats["errors"])
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error in sync_instances_between_dcim_and_backend: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            try:
                self.db.rollback()
            except:
                pass
            
            return {
                "success": False,
                "error": str(e)
            }
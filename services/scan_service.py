# services/scan_service.py - Updated với SSH debugging và fixes
import asyncio
import json
import tempfile
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException
import subprocess
import yaml
import stat

from models.server import Server
from models.sshkey import SshKey
from dao.server_dao import ServerDao
from dao.ssh_key_dao import SshKeyDao


class ScanService:
    
    @staticmethod
    async def simple_scan(db: Session, server_id: int) -> Dict[str, Any]:
        """
        Thực hiện scan đơn giản với debug SSH connection
        """
        try:
            # Lấy thông tin server
            server = ServerDao.get_server_by_id(db, server_id)
            if not server:
                raise HTTPException(status_code=404, detail="Server not found")
            
            if not server.ssh_key_id:
                raise HTTPException(status_code=400, detail="Server không có SSH key")
            
            # Lấy SSH key
            ssh_key = SshKeyDao.get_by_id(db, server.ssh_key_id)
            if not ssh_key:
                raise HTTPException(status_code=400, detail="SSH key not found")
            
            print(f"🔍 Debug: Server {server.name} ({server.ip_address}:{server.ssh_port})")
            print(f"🔍 Debug: SSH Key {ssh_key.name} ({ssh_key.key_type})")
            
            # Tạo file SSH key tạm thời với proper permissions
            ssh_key_path = await ScanService._create_temp_ssh_key_secure(ssh_key.private_key)

            try:
                # Thực hiện các lệnh scan cơ bản
                basic_commands = [
                    ("pwd", "Get current directory"),
                    ("whoami", "Get current user"),
                    ("hostname", "Get hostname"),
                    ("uname -a", "Get system information"),
                    ("df -h", "Get disk usage"),
                    ("free -h", "Get memory usage"),
                    ("uptime", "Get system uptime")
                ]
                
                results = {}
                for command, description in basic_commands:
                    try:
                        print(f"🔍 Executing: {command}")
                        result = await ScanService._execute_ssh_command_secure(
                            server.ip_address, 
                            server.ssh_port,
                            ssh_key_path,
                            command
                        )
                        results[command] = {
                            "description": description,
                            "output": result["stdout"],
                            "error": result["stderr"],
                            "return_code": result["return_code"],
                            "success": result["return_code"] == 0
                        }
                        
                        if result["return_code"] == 0:
                            print(f"✅ {command}: SUCCESS")
                        else:
                            print(f"❌ {command}: FAILED - {result['stderr']}")
                            
                    except Exception as e:
                        print(f"❌ {command}: EXCEPTION - {str(e)}")
                        results[command] = {
                            "description": description,
                            "output": "",
                            "error": str(e),
                            "return_code": -1,
                            "success": False
                        }
                
                return {
                    "server_id": server_id,
                    "server_name": server.name,
                    "ip_address": server.ip_address,
                    "scan_time": datetime.now().isoformat(),
                    "scan_type": "simple",
                    "results": results
                }
                
            finally:
                # Xóa file SSH key tạm thời
                if os.path.exists(ssh_key_path):
                    os.remove(ssh_key_path)
                    print(f"🗑️ Cleaned up temp SSH key: {ssh_key_path}")
                    
        except Exception as e:
            print(f"❌ Scan failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")
    
    @staticmethod
    async def _create_temp_ssh_key_secure(private_key: str) -> str:
        """
        Tạo file SSH key tạm thời với proper security permissions
        """
        # Tạo file tạm thời trong /tmp với secure permissions
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='_ssh_key', prefix='scan_') as key_file:
            key_file.write(private_key)
            key_path = key_file.name
        
        # Set proper permissions (owner read only)
        os.chmod(key_path, stat.S_IRUSR)  # 0o400 - read only for owner
        
        print(f"🔑 Created secure temp SSH key: {key_path}")
        print(f"🔍 Key permissions: {oct(os.stat(key_path).st_mode)[-3:]}")
        
        return key_path
    
    @staticmethod
    async def _execute_ssh_command_secure(
        host: str, 
        port: int, 
        ssh_key_path: str, 
        command: str
    ) -> Dict[str, Any]:
        """
        Thực hiện SSH command với secure options và debugging
        """
        cmd = [
            'ssh',
            '-i', ssh_key_path,
            '-p', str(port),
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'PreferredAuthentications=publickey',  # Chỉ dùng publickey
            '-o', 'PasswordAuthentication=no',           # Disable password auth  
            '-o', 'PubkeyAuthentication=yes',            # Enable publickey auth
            '-o', 'IdentitiesOnly=yes',                  # Chỉ dùng key được chỉ định
            '-o', 'ConnectTimeout=10',                   # Timeout sau 10s
            '-o', 'BatchMode=yes',                       # Non-interactive mode
            f'root@{host}',
            command
        ]
        
        print(f"🔍 SSH Command: {' '.join(cmd[:8])} ... {command}")
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait với timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=30
            )
            
            result = {
                "return_code": process.returncode,
                "stdout": stdout.decode('utf-8'),
                "stderr": stderr.decode('utf-8')
            }
            
            # Debug output
            if process.returncode != 0:
                print(f"❌ SSH failed with return code: {process.returncode}")
                print(f"❌ STDERR: {result['stderr']}")
            
            return result
            
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return {
                "return_code": -1,
                "stdout": "",
                "stderr": "SSH command timed out after 30 seconds"
            }
        except Exception as e:
            return {
                "return_code": -1,
                "stdout": "",
                "stderr": f"SSH execution failed: {str(e)}"
            }

    @staticmethod
    async def test_ssh_connection_debug(db: Session, server_id: int) -> Dict[str, Any]:
        """
        Test SSH connection với detailed debugging
        """
        try:
            server = ServerDao.get_server_by_id(db, server_id)
            if not server:
                raise HTTPException(status_code=404, detail="Server not found")
            
            ssh_key = SshKeyDao.get_by_id(db, server.ssh_key_id)
            if not ssh_key:
                raise HTTPException(status_code=400, detail="SSH key not found")
            
            print(f"🔍 Testing SSH connection to {server.ip_address}:{server.ssh_port}")
            
            # Test 1: SSH key format validation
            ssh_key_path = await ScanService._create_temp_ssh_key_secure(ssh_key.private_key)
            
            try:
                # Test 2: SSH với single simple command
                result = await ScanService._execute_ssh_command_secure(
                    server.ip_address,
                    server.ssh_port, 
                    ssh_key_path,
                    "echo 'SSH Test Successful'"
                )
                
                return {
                    "server_id": server_id,
                    "connection_test": {
                        "success": result["return_code"] == 0,
                        "return_code": result["return_code"],
                        "output": result["stdout"],
                        "error": result["stderr"]
                    },
                    "debug_info": {
                        "server_ip": server.ip_address,
                        "ssh_port": server.ssh_port,
                        "ssh_key_type": ssh_key.key_type.value,
                        "temp_key_path": ssh_key_path
                    }
                }
                
            finally:
                if os.path.exists(ssh_key_path):
                    os.remove(ssh_key_path)
                    
        except Exception as e:
            print(f"❌ Connection test failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")
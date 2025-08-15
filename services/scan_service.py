# services/scan_service.py - Fixed version with SSH debugging
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
    async def debug_ssh_key(db: Session, server_id: int) -> Dict[str, Any]:
        """
        Debug SSH key và connection chi tiết
        """
        try:
            server = ServerDao.get_server_by_id(db, server_id)
            if not server:
                raise HTTPException(status_code=404, detail="Server not found")
            
            ssh_key = SshKeyDao.get_by_id(db, server.ssh_key_id)
            if not ssh_key:
                raise HTTPException(status_code=400, detail="SSH key not found")
            
            print(f"🔍 Debug SSH Key Details:")
            print(f"   - SSH Key ID: {ssh_key.id}")
            print(f"   - SSH Key Name: {ssh_key.name}")
            print(f"   - SSH Key Type: {ssh_key.key_type}")
            print(f"   - Public Key: {ssh_key.public_key[:50]}...")
            print(f"   - Private Key Length: {len(ssh_key.private_key)} chars")
            print(f"   - Fingerprint: {ssh_key.fingerprint}")
            
            # Validate SSH key format
            private_key_content = ScanService._validate_and_fix_ssh_key(ssh_key.private_key)
            ssh_key_path = await ScanService._create_temp_ssh_key_secure(private_key_content)
            
            try:
                # Test với verbose SSH
                cmd = [
                    'ssh',
                    '-i', ssh_key_path,
                    '-p', str(server.ssh_port),
                    '-o', 'StrictHostKeyChecking=no',
                    '-o', 'UserKnownHostsFile=/dev/null',
                    '-o', 'PasswordAuthentication=no',
                    '-o', 'PubkeyAuthentication=yes',
                    '-o', 'IdentitiesOnly=yes',
                    '-vvv',  # Very verbose
                    f"maybetuandat@{server.ip_address}",
                    "echo 'SSH Debug Test'"
                ]
                
                print(f"🔍 Running verbose SSH test...")
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=30.0
                )
                
                return {
                    "server_info": {
                        "id": server.id,
                        "name": server.name,
                        "ip": server.ip_address,
                        "port": server.ssh_port
                    },
                    "ssh_key_info": {
                        "id": ssh_key.id,
                        "name": ssh_key.name,
                        "type": ssh_key.key_type.value,
                        "fingerprint": ssh_key.fingerprint,
                        "public_key_start": ssh_key.public_key[:100],
                        "private_key_length": len(ssh_key.private_key)
                    },
                    "connection_test": {
                        "return_code": process.returncode,
                        "stdout": stdout.decode('utf-8') if stdout else "",
                        "stderr": stderr.decode('utf-8') if stderr else ""
                    }
                }
                
            finally:
                if os.path.exists(ssh_key_path):
                    os.remove(ssh_key_path)
                    
        except Exception as e:
            print(f"❌ Debug failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Debug failed: {str(e)}")

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
            
            # FIXED: Validate SSH key format trước khi tạo file
            private_key_content = ScanService._validate_and_fix_ssh_key(ssh_key.private_key)
            
            # Tạo file SSH key tạm thời với proper permissions
            ssh_key_path = await ScanService._create_temp_ssh_key_secure(private_key_content)

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
                        # Use maybetuandat username instead of root
                        result = await ScanService._execute_ssh_command_secure(
                            server.ip_address, 
                            server.ssh_port,
                            ssh_key_path,
                            command,
                            username="maybetuandat"
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
    async def test_connection(db: Session, server_id: int) -> Dict[str, Any]:
        """
        Test SSH connection với debugging tốt hơn
        """
        try:
            server = ServerDao.get_server_by_id(db, server_id)
            if not server:
                raise HTTPException(status_code=404, detail="Server not found")
            
            ssh_key = SshKeyDao.get_by_id(db, server.ssh_key_id)
            if not ssh_key:
                raise HTTPException(status_code=400, detail="SSH key not found")
            
            print(f"🔍 Testing SSH connection to {server.ip_address}:{server.ssh_port}")
            
            # FIXED: Validate SSH key format
            private_key_content = ScanService._validate_and_fix_ssh_key(ssh_key.private_key)
            
            # Test SSH key format validation
            ssh_key_path = await ScanService._create_temp_ssh_key_secure(private_key_content)
            
            try:
                # Use maybetuandat username instead of root
                result = await ScanService._execute_ssh_command_secure(
                    server.ip_address,
                    server.ssh_port, 
                    ssh_key_path,
                    "echo 'SSH Test Successful'",
                    username="maybetuandat"
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
                        "username": "maybetuandat",
                        "temp_key_path": ssh_key_path
                    }
                }
                
            finally:
                if os.path.exists(ssh_key_path):
                    os.remove(ssh_key_path)
                    
        except Exception as e:
            print(f"❌ Connection test failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")
    
    @staticmethod
    def _validate_and_fix_ssh_key(private_key: str) -> str:
        """
        FIXED: Validate và fix SSH key format
        """
        # Remove any extra whitespace
        key_content = private_key.strip()
        
        # Ensure proper newlines
        if '\\n' in key_content:
            # Fix escaped newlines
            key_content = key_content.replace('\\n', '\n')
        
        # Ensure key starts and ends properly
        if not key_content.startswith('-----BEGIN'):
            raise ValueError("Invalid private key: must start with -----BEGIN")
        
        if not key_content.endswith('-----'):
            raise ValueError("Invalid private key: must end with -----")
        
        # Ensure final newline
        if not key_content.endswith('\n'):
            key_content += '\n'
        
        # Validate base64 content (between headers)
        lines = key_content.split('\n')
        header_found = False
        footer_found = False
        
        for line in lines:
            if line.startswith('-----BEGIN'):
                header_found = True
            elif line.startswith('-----END'):
                footer_found = True
                break
        
        if not header_found or not footer_found:
            raise ValueError("Invalid private key: missing header or footer")
        
        print(f"🔧 SSH key validation passed, length: {len(key_content)}")
        return key_content
    
    @staticmethod
    async def _create_temp_ssh_key_secure(private_key: str) -> str:
        """
        FIXED: Tạo file SSH key tạm thời với proper security permissions
        """
        # Tạo file tạm thời trong /tmp với secure permissions
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='_ssh_key', prefix='scan_') as key_file:
            key_file.write(private_key)
            key_path = key_file.name
        
        # Set proper permissions (owner read only)
        os.chmod(key_path, stat.S_IRUSR)  # 0o400 - read only for owner
        
        print(f"🔑 Created secure temp SSH key: {key_path}")
        print(f"🔍 Key permissions: {oct(os.stat(key_path).st_mode)[-3:]}")
        
        # FIXED: Verify file was written correctly
        with open(key_path, 'r') as f:
            content = f.read()
            print(f"🔍 Key file size: {len(content)} bytes")
            print(f"🔍 Key starts with: {content[:20]}...")
            print(f"🔍 Key ends with: ...{content[-20:]}")
        
        return key_path
    
    @staticmethod
    async def _execute_ssh_command_secure(
        host: str, 
        port: int, 
        ssh_key_path: str, 
        command: str,
        username: str = "maybetuandat"  # FIXED: Change default username
    ) -> Dict[str, Any]:
        """
        FIXED: Thực hiện SSH command với secure options và debugging
        """
        # FIXED: Add username to SSH command
        target = f"{username}@{host}"
        
        cmd = [
            'ssh',
            '-i', ssh_key_path,
            '-p', str(port),
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'PreferredAuthentications=publickey',  # Chỉ dùng publickey
            '-o', 'PasswordAuthentication=no',           # Disable password auth  
            '-o', 'PubkeyAuthentication=yes',            # Enable pubkey auth
            '-o', 'IdentitiesOnly=yes',                  # FIXED: Only use specified key
            '-o', 'LogLevel=ERROR',                      # FIXED: Reduce SSH debug noise
            '-o', 'ConnectTimeout=10',                   # FIXED: Add timeout
            target,  # FIXED: username@host format
            command
        ]
        
        print(f"🔍 SSH Command: ssh -i {ssh_key_path} -p {port} -o StrictHostKeyChecking=no -o ... {target} {command}")
        
        try:
            # FIXED: Use asyncio.create_subprocess_exec for better control
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for completion with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=30.0  # 30 second timeout
            )
            
            stdout_str = stdout.decode('utf-8') if stdout else ""
            stderr_str = stderr.decode('utf-8') if stderr else ""
            return_code = process.returncode
            
            if return_code == 0:
                print(f"✅ SSH command succeeded: {command}")
            else:
                print(f"❌ SSH failed with return code: {return_code}")
                print(f"❌ STDERR: {stderr_str}")
            
            return {
                "stdout": stdout_str,
                "stderr": stderr_str,
                "return_code": return_code
            }
            
        except asyncio.TimeoutError:
            print(f"⏱️ SSH command timeout: {command}")
            return {
                "stdout": "",
                "stderr": "Command timeout",
                "return_code": 124
            }
        except Exception as e:
            print(f"❌ SSH command exception: {str(e)}")
            return {
                "stdout": "",
                "stderr": str(e),
                "return_code": 255
            }
import json
import logging
import os
import subprocess
import tempfile
from typing import Any, Dict, List
from schemas.connection import ServerConnectionInfo, ServerConnectionResult, TestConnectionRequest, TestConnectionResponse
import time

from services.server_service import ServerService

class ConnectionService:
    def __init__(self):
        self.ansible_timeout = 30
        self.max_forks = 20
     


    def test_multiple_connections(self, request: TestConnectionRequest) -> TestConnectionResponse:
        
        try:
            # Tạo inventory cho tất cả servers
            inventory_content = self._create_multiserver_inventory(request.servers)
           

            with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as inventory_file:
                inventory_file.write(inventory_content)
                inventory_path = inventory_file.name
            
            try:
               
                ansible_results = self._run_ansible_multiple_hosts(inventory_path, request.servers)
                
               
                results = self._parse_mixed_results(ansible_results, request.servers)
                
                successful_count = sum(1 for r in results if r.status == "success")
                
              
                
                return TestConnectionResponse(
                    total_servers=len(request.servers),
                    successful_connections=successful_count,
                    failed_connections=len(request.servers) - successful_count,
                    results=results
                )
                
            finally:
                # Cleanup inventory file
                if os.path.exists(inventory_path):
                    os.unlink(inventory_path)
                    
        except Exception as e:
            print(f"❌ Service error: {str(e)}")
            logging.error(f"Error testing multiple server connections: {str(e)}")
            
            # Tạo failed results cho tất cả servers
            failed_results = []
            for server in request.servers:
                failed_results.append(ServerConnectionResult(
                    ip=server.ip,
                    ssh_user=server.ssh_user,
                    ssh_port=server.ssh_port,
                    status="failed",
                    message="Service error",
                    error_details=str(e)
                ))
            
            return TestConnectionResponse(
                total_servers=len(request.servers),
                successful_connections=0,
                failed_connections=len(request.servers),
                results=failed_results
            )

    def _create_multiserver_inventory(self, servers: List[ServerConnectionInfo]) -> str:
        inventory_content = "[test_servers]\n"
        
        for server in servers:
            inventory_content += (
                f"{server.ip} "
                f"ansible_host={server.ip} "
                f"ansible_user={server.ssh_user} "
                f"ansible_password={server.ssh_password} "
                f"ansible_port={server.ssh_port} "
                f"ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10' "
                f"ansible_ssh_pass={server.ssh_password} "
                f"ansible_connection=ssh\n"
            )
        return inventory_content

    def _run_ansible_multiple_hosts(self, inventory_path: str, servers: List[ServerConnectionInfo]) -> Dict[str, Any]:
        try:
            forks = min(self.max_forks, len(servers))

            # tao cau lenh de thuc hien lay cac tham so tu servers 
            system_info_cmd = (
                "echo 'HOSTNAME:' && hostname && "
                "echo 'OS_INFO:' && "
                "(cat /etc/os-release 2>/dev/null | grep -E '^(PRETTY_NAME|NAME|VERSION_ID)=' || "
                "cat /etc/redhat-release 2>/dev/null || "
                "uname -s) && "
                "echo 'UPTIME:' && uptime"
            )
            
            cmd = [
                "ansible",
                "test_servers",
                "-i", inventory_path,
                "-m", "shell",
                "-a", system_info_cmd,
                "--timeout", str(self.ansible_timeout),
                "--forks", str(forks),
            ]
            
            
            # su dung subprocess de chay ansible command 
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=(self.ansible_timeout + 10) * len(servers) // forks + 30
            )
            
            
            
            return {
                "success": True,  
                "stdout": result.stdout,
                "returncode": result.returncode
            }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Ansible execution timeout",
                "stdout": "",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Ansible execution error: {str(e)}",
                "stdout": ""
            }

    def _parse_mixed_results(self, ansible_results: Dict[str, Any], servers: List[ServerConnectionInfo]) -> List[ServerConnectionResult]:
        
        results = []
        
        try:
            # Lấy output từ cả stdout và stderr
            all_output = ansible_results.get("stdout", "")
          
          
            

            for i, server in enumerate(servers):
                try:
                    
                    # doi voi moi con server thi find theo ip mot lan de lay ket qua 
                    server_result = self._parse_server_from_mixed_output(all_output, server)
                    results.append(server_result)
                   
                except Exception as e:
                    print(f" Error parsing server {server.ip}: {str(e)}")
                    results.append(ServerConnectionResult(
                        ip=server.ip,
                        ssh_user=server.ssh_user,
                        ssh_port=server.ssh_port,
                        status="failed",
                        message="Parse error",
                        error_details=str(e)
                    ))
            
        except Exception as e:
            print(f" Error in parse_mixed_results: {str(e)}")
            # Tạo failed results cho tất cả servers
            for server in servers:
                results.append(ServerConnectionResult(
                    ip=server.ip,
                    ssh_user=server.ssh_user,
                    ssh_port=server.ssh_port,
                    status="failed",
                    message="Parse error",
                    error_details=str(e)
                ))
        
        return results

    def _parse_server_from_mixed_output(self, all_output: str, server: ServerConnectionInfo) -> ServerConnectionResult:
        
        try:
            server_ip = server.ip
            
            
            # Tìm tất cả dòng liên quan đến server này
            lines = all_output.split('\n')
            server_lines = []
            
            for line in lines:
                if server_ip in line:
                    server_lines.append(line.strip())
            
            server_text = '\n'.join(server_lines)
            
            
            
            # Phân tích trạng thái server
            status_analysis = self._analyze_server_status(server_text, all_output, server_ip)
            
            if status_analysis["status"] == "success":
            
                return self._create_success_result(server, status_analysis["details"])
            else:
                print(f" {server_ip}: {status_analysis['reason']}")
                return self._create_failed_result(
                    server, 
                    status_analysis["reason"], 
                    status_analysis["message"],
                    status_analysis["details"]
                )
                
        except Exception as e:
            print(f" Exception parsing server {server.ip}: {str(e)}")
            return self._create_failed_result(server, "Parse Error", "Lỗi phân tích kết quả", str(e))

    def _analyze_server_status(self, server_text: str, all_output: str, server_ip: str) -> Dict[str, Any]:
    
        
        # Case 1: Server unreachable/failed to connect
        unreachable_patterns = [
            "UNREACHABLE",
            "unreachable", 
            "Connection timed out",
            "No route to host",
            "Connection refused",
            "Host is unreachable",
            "SSH Error",
            "Permission denied",
            "Authentication failure"
        ]
        
        for pattern in unreachable_patterns:
            if pattern in server_text:
                return {
                    "status": "failed",
                    "reason": "Unreachable",
                    "message": f"Không thể kết nối: {pattern}",
                    "details": server_text[:300]
                }
        
        # Case 2: Server command failed
        if "FAILED" in server_text or "failed" in server_text:
            return {
                "status": "failed",
                "reason": "Command Failed",
                "message": "Kết nối được nhưng command thất bại",
                "details": server_text[:300]
            }
        
        # Case 3: Server success patterns
        success_patterns = [
            f"{server_ip} | CHANGED",
            f"{server_ip} | SUCCESS"
        ]
        
        for pattern in success_patterns:
            if pattern in all_output:
                return {
                    "status": "success",
                    "reason": "Success",
                    "message": "Kết nối thành công",
                    "details": self._extract_server_success_details(all_output, server_ip)
                }
        
        # Case 4: Có output nhưng không rõ ràng
        if server_text.strip():
            # Nếu có HOSTNAME: trong output gần server IP này
            lines = all_output.split('\n')
            for i, line in enumerate(lines):
                if server_ip in line:
                    # Check vài dòng sau có HOSTNAME: không
                    for j in range(i+1, min(i+10, len(lines))):
                        if "HOSTNAME:" in lines[j]:
                            return {
                                "status": "success",
                                "reason": "Success",
                                "message": "Kết nối thành công",
                                "details": self._extract_server_success_details(all_output, server_ip)
                            }
                    break
            
            # Fallback: có output nhưng không success
            return {
                "status": "failed",
                "reason": "Unclear Status",
                "message": "Có phản hồi nhưng không rõ trạng thái",
                "details": server_text[:300]
            }
        
        # Case 5: Không có output nào
        return {
            "status": "failed",
            "reason": "No Response",
            "message": "Không có phản hồi từ server",
            "details": "No output found for this server"
        }

    def _extract_server_success_details(self, all_output: str, server_ip: str) -> Dict[str, str]:
        
        details = {"hostname": "Unknown", "os_version": "Unknown"}
        
        try:
            lines = all_output.split('\n')
            
            # Tìm vị trí của server IP
            server_line_index = -1
            for i, line in enumerate(lines):
                if server_ip in line and ("CHANGED" in line or "SUCCESS" in line):
                    server_line_index = i
                    break
            
            if server_line_index >= 0:
                # Tìm HOSTNAME: và OS_INFO: trong vài dòng tiếp theo
                for i in range(server_line_index + 1, min(server_line_index + 20, len(lines))):
                    line = lines[i].strip()
                    
                    if line == "HOSTNAME:" and i + 1 < len(lines):
                        details["hostname"] = lines[i + 1].strip()
                    
                    elif line == "OS_INFO:":
                        for j in range(i + 1, min(i + 5, len(lines))):
                            os_line = lines[j].strip()
                            if not os_line or os_line.startswith("UPTIME:"):
                                break
                            
                            if "PRETTY_NAME=" in os_line:
                                details["os_version"] = os_line.split("PRETTY_NAME=")[1].strip('"\'')
                                break
                            elif "release" in os_line.lower():
                                details["os_version"] = os_line
                                break
                        break
        
        except Exception as e:
            print(f"⚠️ Error extracting details for {server_ip}: {e}")
        
        return details

    def _create_success_result(self, server: ServerConnectionInfo, details: Dict[str, str]) -> ServerConnectionResult:
        """Tạo success result cho server"""
        return ServerConnectionResult(
            ip=server.ip,
            ssh_user=server.ssh_user,
            ssh_port=server.ssh_port,
            status="success",
            message="Kết nối thành công",
            hostname=details.get("hostname", "Unknown"),
            os_version=details.get("os_version", "Unknown")
        )

    def _create_failed_result(self, server: ServerConnectionInfo, reason: str, message: str, error_details: str) -> ServerConnectionResult:
        """Tạo failed result cho server"""
        clean_error = str(error_details).strip()
        if len(clean_error) > 300:
            clean_error = clean_error[:300] + "..."
        
        return ServerConnectionResult(
            ip=server.ip,
            ssh_user=server.ssh_user,
            ssh_port=server.ssh_port,
            status="failed",
            message=message,
            error_details=clean_error
        )
    def test_single_connection(self, server: ServerConnectionInfo) -> ServerConnectionResult:
        request = TestConnectionRequest(servers=[server])
        response = self.test_multiple_connections(request)
        if response.results:
            return response.results[0]
        
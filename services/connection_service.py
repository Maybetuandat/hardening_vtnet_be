import json
import logging
import os
import subprocess
import tempfile
from typing import Any, Dict, List
from schemas.connection import ServerConnectionInfo, ServerConnectionResult, TestConnectionRequest, TestConnectionResponse
import time

class ConnectionService:
    def __init__(self):
        self.ansible_timeout = 30
        self.max_forks = 20

    def test_multiple_connections(self, request: TestConnectionRequest) -> TestConnectionResponse:
        start_time = time.time()

        try:
            # Tạo inventory cho tất cả servers
            inventory_content = self._create_multiserver_inventory(request.servers)

            with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as inventory_file:
                inventory_file.write(inventory_content)
                inventory_path = inventory_file.name
            
            try:
                # Chạy ansible cho tất cả servers
                ansible_results = self._run_ansible_multiple_hosts(inventory_path, request.servers)
                
                # Parse kết quả
                results = self._parse_multiple_results(ansible_results, request.servers)
                
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
            logging.error(f"Error testing multiple server connections: {str(e)}")
            return TestConnectionResponse(
                total_servers=len(request.servers),
                successful_connections=0,
                failed_connections=len(request.servers),
                results=[
                    ServerConnectionResult(
                        ip=server.ip,
                        ssh_user=server.ssh_user,
                        ssh_port=server.ssh_port,
                        status="failed",
                        message="Service error",
                        error_details=str(e)
                    ) for server in request.servers
                ]
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
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=(self.ansible_timeout + 10) * len(servers) // forks + 30
            )
            
           
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
                
        except subprocess.TimeoutExpired:
         
            return {
                "success": False,
                "error": f"Ansible execution timeout",
                "stdout": "",
                "stderr": ""
            }
        except Exception as e:
            print(f"❌ Ansible execution error: {str(e)}")
            return {
                "success": False,
                "error": f"Ansible execution error: {str(e)}",
                "stdout": "",
                "stderr": ""
            }

    def _parse_multiple_results(self, ansible_results: Dict[str, Any], servers: List[ServerConnectionInfo]) -> List[ServerConnectionResult]:
        """Parse kết quả dựa vào return code thay vì text parsing"""
        results = []
        
        # Kiểm tra return code trước
        if ansible_results["returncode"] != 0:
            # Ansible command thất bại hoàn toàn
            print(f"❌ Ansible command failed with return code: {ansible_results['returncode']}")
            for server in servers:
                results.append(ServerConnectionResult(
                    ip=server.ip,
                    ssh_user=server.ssh_user,
                    ssh_port=server.ssh_port,
                    status="failed",
                    message="Ansible command failed",
                    error_details=ansible_results.get("error", f"Return code: {ansible_results['returncode']}")
                ))
            return results
        
        # Return code = 0, nghĩa là thành công
        print(f"✅ Ansible command succeeded (rc=0)")
        
        stdout = ansible_results["stdout"]
        stderr = ansible_results["stderr"]
        
        # Track servers đã có kết quả
        server_results = {}
        
        # Parse từ stdout (stderr chỉ là warnings)
        all_output = stdout.strip()
        
        print(f"🔍 Parsing output for {len(servers)} servers")
        
        if all_output:
            # Parse theo từng server riêng biệt
            for server in servers:
                server_ip = server.ip
                
                # Tìm output của server này
                server_lines = []
                lines = all_output.split('\n')
                
                # Thu thập tất cả lines liên quan đến server này
                collecting = False
                for line in lines:
                    if server_ip in line:
                        collecting = True
                        server_lines.append(line)
                    elif collecting and (line.startswith(' ') or line.strip() == ''):
                        # Dòng continuation hoặc dòng trống
                        server_lines.append(line)
                    elif collecting and any(other_server.ip in line for other_server in servers if other_server.ip != server_ip):
                        # Gặp server khác = dừng collect
                        collecting = False
                    elif collecting:
                        # Dòng khác nhưng vẫn đang collect
                        server_lines.append(line)
                
                # Join all lines for this server
                server_output = '\n'.join(server_lines)
                
                print(f"🔍 Server {server_ip} output ({len(server_output)} chars)")
                
                # Với return code = 0, tất cả servers trong stdout đều thành công
                # Chỉ cần check xem server có trong output không
                if server_ip in server_output:
                    # Parse thông tin từ output
                    server_result = self._parse_success_output(server_output, server)
                    print(f"✅ {server_ip}: Parsed successfully")
                else:
                    # Server không có trong output = có thể failed
                    print(f"❓ {server_ip}: Not found in output")
                    server_result = ServerConnectionResult(
                        ip=server.ip,
                        ssh_user=server.ssh_user,
                        ssh_port=server.ssh_port,
                        status="failed",
                        message="Server not found in output",
                        error_details="No output received for this server"
                    )
                
                server_results[server_ip] = server_result
        
        # Convert dict to list, đảm bảo tất cả servers đều có kết quả
        for server in servers:
            if server.ip in server_results:
                results.append(server_results[server.ip])
            else:
                # Server không có kết quả = failed
                results.append(ServerConnectionResult(
                    ip=server.ip,
                    ssh_user=server.ssh_user,
                    ssh_port=server.ssh_port,
                    status="failed",
                    message="No result for server",
                    error_details="Server did not appear in ansible output"
                ))
        
        return results

    def _parse_success_output(self, server_output: str, server: ServerConnectionInfo) -> ServerConnectionResult:
        """Parse output từ shell command - nhẹ và dễ parse hơn"""
        try:
            print(f"🔍 Parsing shell command output for {server.ip}")
            print(f"📄 Output: {server_output}")
            
            hostname = "Unknown"
            os_version = "Unknown"
            
            # Parse output từ shell command
            lines = server_output.split('\n')
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Tìm hostname
                if line == "HOSTNAME:" and i + 1 < len(lines):
                    hostname = lines[i + 1].strip()
                    print(f"🏷️ Found hostname: {hostname}")
                
                # Tìm OS info
                elif line == "OS_INFO:":
                    # Đọc các dòng tiếp theo để tìm OS info
                    for j in range(i + 1, min(i + 5, len(lines))):
                        os_line = lines[j].strip()
                        if not os_line or os_line.startswith("UPTIME:"):
                            break
                            
                        # Parse /etc/os-release format
                        if "PRETTY_NAME=" in os_line:
                            os_version = os_line.split("PRETTY_NAME=")[1].strip('"\'')
                            break
                        elif "NAME=" in os_line and "VERSION_ID=" in server_output:
                            # Tìm NAME và VERSION_ID
                            name = ""
                            version = ""
                            for k in range(i + 1, min(i + 5, len(lines))):
                                check_line = lines[k].strip()
                                if "NAME=" in check_line and not "PRETTY_NAME=" in check_line:
                                    name = check_line.split("NAME=")[1].strip('"\'')
                                elif "VERSION_ID=" in check_line:
                                    version = check_line.split("VERSION_ID=")[1].strip('"\'')
                            
                            if name and version:
                                os_version = f"{name} {version}"
                                break
                            elif name:
                                os_version = name
                                break
                        
                        # Fallback: RedHat release format
                        elif "release" in os_line.lower():
                            os_version = os_line
                            break
                        
                        # Fallback: uname output
                        elif any(keyword in os_line for keyword in ["Linux", "Ubuntu", "CentOS", "RedHat", "RHEL"]):
                            os_version = os_line
                            break
                    
                    print(f"💾 Found OS: {os_version}")
                    break
            
            print(f"🎯 Final result - hostname: {hostname}, os: {os_version}")
            
            return ServerConnectionResult(
                ip=server.ip,
                ssh_user=server.ssh_user,
                ssh_port=server.ssh_port,
                status="success",
                message="Kết nối thành công",
                hostname=hostname,
                os_version=os_version
            )
                        
        except Exception as e:
            print(f"❌ Error parsing shell output for {server.ip}: {e}")
        
        # Fallback
        print(f"⚠️ Using fallback for {server.ip}")
        return ServerConnectionResult(
            ip=server.ip,
            ssh_user=server.ssh_user,
            ssh_port=server.ssh_port,
            status="success",
            message="Kết nối thành công",
            hostname="Unknown",
            os_version="Unknown"
        )

    def _parse_failed_output(self, server_output: str, server: ServerConnectionInfo) -> ServerConnectionResult:
        """Parse output thất bại cho server"""
        error_msg = "Connection failed"
        
        if "UNREACHABLE" in server_output:
            error_msg = "Server unreachable"
        elif "FAILED" in server_output:
            error_msg = "Command execution failed"
        
        # Extract chi tiết lỗi
        error_detail = server_output.strip()
        
        # Tìm phần error message cụ thể
        if "=>" in server_output:
            parts = server_output.split("=>", 1)
            if len(parts) > 1:
                error_detail = parts[1].strip()
        elif ":" in server_output:
            parts = server_output.split(":", 1)
            if len(parts) > 1 and "UNREACHABLE" in parts[0]:
                error_detail = parts[1].strip()
        
        print(f"❌ Parsed error for {server.ip}: {error_msg}")
        
        return ServerConnectionResult(
            ip=server.ip,
            ssh_user=server.ssh_user,
            ssh_port=server.ssh_port,
            status="failed",
            message=error_msg,
            error_details=error_detail[:500]  # Limit error detail length
        )
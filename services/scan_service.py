# services/compliance_scan_service.py
import logging
import os
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from dao.server_dao import ServerDAO
from models.compliance_result import ComplianceResult
from models.rule_result import RuleResult
from models.server import Server
from models.rule import Rule
from models.command import Command
from schemas.compliance import ComplianceScanRequest, ComplianceScanResponse
from services.workload_service import WorkloadService
from services.compliance_result_service import ComplianceResultService


class ComplianceScanService:
    """Service chuyên xử lý logic scan servers"""
    
    def __init__(self, db: Session):
        self.db = db
        self.server_dao = ServerDAO(db)
        self.workload_service = WorkloadService(db)
        self.compliance_result_service = ComplianceResultService(db)
        
        # Ansible configuration
        self.ansible_timeout = 30

    def start_compliance_scan(self, scan_request: ComplianceScanRequest) -> ComplianceScanResponse:
        """
        Entry point cho compliance scan
        2 modes: Specific server IDs hoặc Scan all servers với pagination
        """
        try:
            if scan_request.server_ids:
                # MODE 1: Scan specific server list
                return self._scan_specific_servers(scan_request)
            else:
                # MODE 2: Scan all servers với pagination  
                return self._scan_all_servers_pagination(scan_request)
        except Exception as e:
            logging.error(f"Error starting compliance scan: {str(e)}")
            raise Exception(f"Lỗi khi bắt đầu quét compliance: {str(e)}")

    def _scan_specific_servers(self, scan_request: ComplianceScanRequest) -> ComplianceScanResponse:
        """MODE 1: Scan danh sách servers cụ thể"""
        servers = []
        for server_id in scan_request.server_ids:
            server = self.server_dao.get_by_id(server_id)
            if server and server.status:  # Chỉ scan servers active
                servers.append(server)
        
        if not servers:
            raise ValueError("Không có server active nào để scan")

        # Tạo ComplianceResult cho từng server
        compliance_result_ids = []
        for server in servers:
            compliance_result = self.compliance_result_service.create_pending_result(server.id)
            compliance_result_ids.append(compliance_result.id)

        # Scan theo batch
        self._process_compliance_scan_batches(servers, scan_request.batch_size)

        return ComplianceScanResponse(
            message=f"Đã bắt đầu quét {len(servers)} servers cụ thể",
            total_servers=len(servers),
            started_scans=compliance_result_ids
        )

    def _scan_all_servers_pagination(self, scan_request: ComplianceScanRequest) -> ComplianceScanResponse:
        """MODE 2: Scan ALL servers bằng database pagination"""
        # Đếm tổng số servers active
        total_servers = self.server_dao.count_active_servers()
        
        if total_servers == 0:
            raise ValueError("Không có server active nào để scan")

        logging.info(f"Starting pagination scan for {total_servers} servers")

        # Scan theo pagination
        all_compliance_ids = self._process_pagination_scan(total_servers, scan_request.batch_size)

        return ComplianceScanResponse(
            message=f"Đã bắt đầu quét {total_servers} servers bằng pagination",
            total_servers=total_servers,
            started_scans=all_compliance_ids
        )

    def _process_pagination_scan(self, total_servers: int, batch_size: int) -> List[int]:
        """Xử lý scan all servers bằng database pagination"""
        all_compliance_ids = []
        current_skip = 0
        batch_number = 1
        
        while current_skip < total_servers:
            try:
                logging.info(f"Processing pagination batch {batch_number}: skip={current_skip}, limit={batch_size}")
                
                # Lấy batch servers từ database
                batch_servers = self.server_dao.get_servers_batch_for_scan(
                    skip=current_skip,
                    limit=batch_size,
                    status=True,
                    order_by="id"
                )
                
                if not batch_servers:
                    logging.info(f"No more servers at skip={current_skip}, stopping pagination")
                    break
                
                # Tạo ComplianceResult cho từng server trong batch
                batch_compliance_ids = []
                for server in batch_servers:
                    compliance_result = self.compliance_result_service.create_pending_result(server.id)
                    batch_compliance_ids.append(compliance_result.id)
                
                all_compliance_ids.extend(batch_compliance_ids)
                
                # Scan batch servers
                self._process_compliance_scan_batches(batch_servers, len(batch_servers))
                
                # Move to next batch
                current_skip += batch_size
                batch_number += 1
                time.sleep(0.2)
                
            except Exception as e:
                logging.error(f"Error processing pagination batch {batch_number}: {str(e)}")
                current_skip += batch_size
                batch_number += 1
                continue
        
        return all_compliance_ids

    def _process_compliance_scan_batches(self, servers: List[Server], batch_size: int):
        """Xử lý quét compliance theo từng batch servers"""
        total_servers = len(servers)
        
        for i in range(0, total_servers, batch_size):
            batch_servers = servers[i:i + batch_size]
            
            logging.info(f"Processing batch {i//batch_size + 1}: servers {i+1}-{min(i+batch_size, total_servers)}")
            
            try:
                # Scan từng server trong batch
                for server in batch_servers:
                    self._scan_single_server(server)
                    
                time.sleep(0.2)
                    
            except Exception as e:
                logging.error(f"Error processing batch {i//batch_size + 1}: {str(e)}")
                continue

    def _scan_single_server(self, server: Server):
        """
        Scan một server với PERSISTENT SSH CONNECTION
        1 server = 1 SSH session cho toàn bộ quá trình
        """
        ssh_connection = None
        try:
            # 1. Lấy pending compliance result
            compliance_result = self.compliance_result_service.get_pending_result_by_server(server.id)
            if not compliance_result:
                logging.warning(f"No pending compliance result found for server {server.hostname}")
                return

            # 2. Update status = running
            self.compliance_result_service.update_status(compliance_result.id, "running")

            # 3. Lấy workload và rules
            workload = self.workload_service.dao.get_by_id(server.workload_id)
            if not workload:
                logging.warning(f"Server {server.hostname} không có workload")
                self.compliance_result_service.update_status(compliance_result.id, "failed")
                return

            rules = self._get_active_rules_by_workload(workload.id)
            if not rules:
                self.compliance_result_service.complete_result(compliance_result.id, [], 0)
                return

            # 4. Tạo persistent SSH connection
            ssh_connection = self._create_persistent_ssh_connection(server)
            if not ssh_connection:
                raise Exception("Cannot establish SSH connection")

            # 5. Thực thi tất cả rules với persistent connection
            rule_results = self._execute_all_rules_with_persistent_connection(
                server, rules, ssh_connection, compliance_result.id
            )

            # 6. Complete compliance result
            self.compliance_result_service.complete_result(compliance_result.id, rule_results, len(rules))
            
            logging.info(f"Server {server.hostname} scan completed successfully")

        except Exception as e:
            logging.error(f"Error scanning server {server.hostname}: {str(e)}")
            try:
                if compliance_result:
                    self.compliance_result_service.update_status(compliance_result.id, "failed")
            except:
                pass
        
        finally:
            # Đóng SSH connection
            if ssh_connection:
                self._close_ssh_connection(ssh_connection)

    def _get_active_rules_by_workload(self, workload_id: int) -> List[Rule]:
        """Lấy danh sách rules active của workload"""
        return self.db.query(Rule).filter(
            Rule.workload_id == workload_id,
            Rule.is_active == True
        ).all()

    def _create_persistent_ssh_connection(self, server: Server) -> Optional[Dict[str, Any]]:
        """Tạo persistent SSH connection với ControlPersist"""
        try:
            control_path = f"/tmp/ansible-ssh-{server.ip_address}-{int(time.time())}"
            
            inventory_content = f"""[target_server]
{server.ip_address} ansible_host={server.ip_address} ansible_user={server.ssh_user} ansible_password={server.ssh_password} ansible_port={server.ssh_port} ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 -o ControlMaster=auto -o ControlPersist=300 -o ControlPath={control_path}' ansible_connection=ssh
"""
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as inventory_file:
                inventory_file.write(inventory_content)
                inventory_path = inventory_file.name
            
            try:
                # Test connection
                cmd = ["ansible", "target_server", "-i", inventory_path, "-m", "ping", "--timeout", "10"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                
                if result.returncode == 0:
                    logging.info(f"Established persistent SSH connection to {server.hostname}")
                    return {
                        "inventory_path": inventory_path,
                        "control_path": control_path,
                        "server": server,
                        "established_at": time.time()
                    }
                else:
                    logging.error(f"Failed SSH connection to {server.hostname}: {result.stderr}")
                    if os.path.exists(inventory_path):
                        os.unlink(inventory_path)
                    return None
                    
            except Exception as e:
                logging.error(f"Error testing SSH connection to {server.hostname}: {str(e)}")
                if os.path.exists(inventory_path):
                    os.unlink(inventory_path)
                return None
                
        except Exception as e:
            logging.error(f"Error creating SSH connection to {server.hostname}: {str(e)}")
            return None

    def _execute_all_rules_with_persistent_connection(
        self, server: Server, rules: List[Rule], ssh_connection: Dict[str, Any], compliance_result_id: int
    ) -> List[RuleResult]:
        """Thực thi tất cả rules với persistent connection"""
        all_rule_results = []
        inventory_path = ssh_connection["inventory_path"]
        
        for i, rule in enumerate(rules):
            try:
                start_time = time.time()
                
                # Lấy commands cho rule và OS version
                commands = self._get_commands_for_rule(rule.id, server.os_version)

                if not commands:
                    # Skipped rule
                    rule_result = RuleResult(
                        compliance_result_id=compliance_result_id,
                        rule_id=rule.id,
                        rule_name=rule.name,
                        status="skipped",
                        message=f"Không có command cho OS {server.os_version}",
                        details="",
                        execution_time=0
                    )
                    all_rule_results.append(rule_result)
                    continue

                # Combine commands
                combined_command = " && ".join([cmd.command_text for cmd in commands])
                
                # Execute với persistent connection
                execution_result = self._execute_command_with_persistent_connection(
                    inventory_path, combined_command
                )
                
                execution_time = int(time.time() - start_time)
                
                # Tạo RuleResult
                if execution_result["success"]:
                    status = "passed"
                    message = "Rule execution successful"
                    details = execution_result["stdout"][:500]
                else:
                    status = "failed"
                    message = "Rule execution failed"
                    details = execution_result["error"][:500]
                
                rule_result = RuleResult(
                    compliance_result_id=compliance_result_id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    status=status,
                    message=message,
                    details=details,
                    execution_time=execution_time
                )
                
                all_rule_results.append(rule_result)
                logging.debug(f"Rule {rule.name} on {server.hostname}: {status} ({execution_time}s)")
                
                # Small delay between rules
                if i < len(rules) - 1:
                    time.sleep(0.1)
                
            except Exception as e:
                logging.error(f"Error executing rule {rule.name} on {server.hostname}: {str(e)}")
                
                # Error result
                rule_result = RuleResult(
                    compliance_result_id=compliance_result_id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    status="error",
                    message="Rule execution error",
                    details=str(e)[:500],
                    execution_time=0
                )
                all_rule_results.append(rule_result)
        
        return all_rule_results

    def _get_commands_for_rule(self, rule_id: int, os_version: str) -> List[Command]:
        """Lấy commands cho rule và OS version"""
        return self.db.query(Command).filter(
            Command.rule_id == rule_id,
            Command.os_version == os_version,
            Command.is_active == True
        ).all()

    def _execute_command_with_persistent_connection(self, inventory_path: str, command: str) -> Dict[str, Any]:
        """Execute command với persistent SSH connection"""
        try:
            cmd = [
                "ansible", "target_server", "-i", inventory_path, "-m", "shell", "-a", command,
                "--timeout", str(self.ansible_timeout)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.ansible_timeout + 5)
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "error": result.stderr if result.returncode != 0 else ""
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timeout", "stdout": "", "stderr": ""}
        except Exception as e:
            return {"success": False, "error": f"Command error: {str(e)}", "stdout": "", "stderr": ""}

    def _close_ssh_connection(self, ssh_connection: Dict[str, Any]):
        """Đóng persistent SSH connection và cleanup"""
        try:
            inventory_path = ssh_connection.get("inventory_path")
            control_path = ssh_connection.get("control_path")
            server = ssh_connection.get("server")
            
            # Đóng ControlMaster
            if control_path and os.path.exists(control_path):
                try:
                    subprocess.run([
                        "ssh", "-o", f"ControlPath={control_path}",
                        "-O", "exit", f"{server.ssh_user}@{server.ip_address}"
                    ], capture_output=True, timeout=5)
                except:
                    pass
                
                # Remove control path
                try:
                    if os.path.exists(control_path):
                        os.unlink(control_path)
                except:
                    pass
            
            # Cleanup inventory file
            if inventory_path and os.path.exists(inventory_path):
                try:
                    os.unlink(inventory_path)
                except:
                    pass
            
            duration = time.time() - ssh_connection.get("established_at", time.time())
            logging.info(f"Closed SSH connection to {server.hostname} (duration: {duration:.1f}s)")
            
        except Exception as e:
            logging.error(f"Error closing SSH connection: {str(e)}")

    def cancel_scan_by_server(self, server_id: int) -> bool:
        """Cancel scan đang chạy cho server"""
        try:
            return self.compliance_result_service.cancel_running_scan_by_server(server_id)
        except Exception as e:
            logging.error(f"Error cancelling scan for server {server_id}: {str(e)}")
            return False
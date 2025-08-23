# services/compliance_service.py
import json
import logging
import os
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
import math

from dao.compliance_dao import ComplianceDAO, RuleResultDAO
from dao.server_dao import ServerDAO
from models.compliance_result import ComplianceResult
from models.rule_result import RuleResult
from models.server import Server
from models.rule import Rule
from models.command import Command
from schemas.compliance import (
    ComplianceResultCreate, ComplianceResultUpdate, ComplianceResultResponse,
    ComplianceResultDetailResponse, ComplianceResultListResponse,
    ComplianceScanRequest, ComplianceScanResponse, ComplianceSearchParams,
    RuleResultCreate, RuleResultResponse
)
from services.server_service import ServerService
from services.workload_service import WorkloadService


class ComplianceService:
    def __init__(self, db: Session):
        self.db = db
        self.dao = ComplianceDAO(db)
        self.rule_result_dao = RuleResultDAO(db)
        self.server_dao = ServerDAO(db)
        self.server_service = ServerService(db)
        self.workload_service = WorkloadService(db)
        
        # Ansible configuration
        self.ansible_timeout = 30

    def get_compliance_results(self, search_params: ComplianceSearchParams) -> ComplianceResultListResponse:
        """Lấy danh sách compliance results với filter"""
        page = max(1, search_params.page)
        page_size = max(1, min(100, search_params.page_size))
        skip = (page - 1) * page_size
        
        results, total = self.dao.search_compliance_results(
            server_id=search_params.server_id,
            workload_id=search_params.workload_id,
            status=search_params.status,
            skip=skip,
            limit=page_size
        )
        
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        result_responses = [self._convert_to_response(result) for result in results]
        
        return ComplianceResultListResponse(
            results=result_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    def get_compliance_result_detail(self, compliance_id: int) -> Optional[ComplianceResultDetailResponse]:
        """Lấy chi tiết compliance result bao gồm rule results"""
        compliance_result = self.dao.get_by_id(compliance_id)
        if not compliance_result:
            return None
            
        # Get server info
        server = self.server_dao.get_by_id(compliance_result.server_id)
        server_hostname = server.hostname if server else "Unknown"
        
        # Get workload info
        workload_name = None
        if server:
            workload = self.workload_service.dao.get_by_id(server.workload_id)
            workload_name = workload.name if workload else "Unknown"
            
        rule_results = self.rule_result_dao.get_by_compliance_id(compliance_id)
        rule_result_responses = [self._convert_rule_result_to_response(rr) for rr in rule_results]
        
        return ComplianceResultDetailResponse(
            id=compliance_result.id,
            server_id=compliance_result.server_id,
            status=compliance_result.status,
            total_rules=compliance_result.total_rules,
            passed_rules=compliance_result.passed_rules,
            failed_rules=compliance_result.failed_rules,
            score=compliance_result.score,
            scan_date=compliance_result.scan_date,
            created_at=compliance_result.created_at,
            updated_at=compliance_result.updated_at,
            rule_results=rule_result_responses,
            server_hostname=server_hostname,
            workload_name=workload_name
        )

    def start_compliance_scan(self, scan_request: ComplianceScanRequest) -> ComplianceScanResponse:
        """
        Bắt đầu quá trình quét compliance cho servers theo batch
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
            compliance_data = ComplianceResultCreate(
                server_id=server.id,
                status="pending",
                total_rules=0,
                passed_rules=0,
                failed_rules=0,
                score=0
            )
            
            compliance_dict = compliance_data.dict()
            compliance_model = ComplianceResult(**compliance_dict)
            compliance_result = self.dao.create(compliance_model)
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
        # Đếm tổng số servers active trong database
        total_servers = self.server_dao.count_active_servers()
        
        if total_servers == 0:
            raise ValueError("Không có server active nào để scan")

        logging.info(f"Starting pagination scan for {total_servers} servers")

        # Tạo ComplianceResults và scan theo pagination
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
                
                # Lấy batch servers từ database với skip/limit
                batch_servers = self.server_dao.get_servers_batch_for_scan(
                    skip=current_skip,
                    limit=batch_size,
                    workload_id=None,  # Không filter theo workload
                    status=True,       # Chỉ servers active
                    order_by="id"      # Order by ID để consistent
                )
                
                if not batch_servers:
                    logging.info(f"No more servers at skip={current_skip}, stopping pagination")
                    break
                
                # Tạo ComplianceResult cho từng server trong batch
                batch_compliance_ids = []
                for server in batch_servers:
                    compliance_data = ComplianceResultCreate(
                        server_id=server.id,
                        status="pending",
                        total_rules=0,
                        passed_rules=0,
                        failed_rules=0,
                        score=0
                    )
                    
                    compliance_dict = compliance_data.dict()
                    compliance_model = ComplianceResult(**compliance_dict)
                    compliance_result = self.dao.create(compliance_model)
                    batch_compliance_ids.append(compliance_result.id)
                
                all_compliance_ids.extend(batch_compliance_ids)
                
                # Scan batch servers
                self._process_compliance_scan_batches(batch_servers, len(batch_servers))
                
                # Move to next batch
                current_skip += batch_size
                batch_number += 1
                
                # Small delay between batches
                time.sleep(0.2)
                
            except Exception as e:
                logging.error(f"Error processing pagination batch {batch_number}: {str(e)}")
                # Continue với batch tiếp theo
                current_skip += batch_size
                batch_number += 1
                continue
        
        return all_compliance_ids

    def _process_compliance_scan_batches(self, servers: List[Server], batch_size: int):
        """Xử lý quét compliance theo từng batch servers"""
        total_servers = len(servers)
        
        # Process servers theo batch
        for i in range(0, total_servers, batch_size):
            batch_servers = servers[i:i + batch_size]
            
            logging.info(f"Processing batch {i//batch_size + 1}: servers {i+1}-{min(i+batch_size, total_servers)}")
            
            try:
                # Xử lý từng server trong batch
                for server in batch_servers:
                    self._scan_single_server(server)
                    
                # Small delay giữa các batch
                time.sleep(0.2)
                    
            except Exception as e:
                logging.error(f"Error processing batch {i//batch_size + 1}: {str(e)}")
                continue

    def _scan_single_server(self, server: Server):
        """
        Scan một server duy nhất với PERSISTENT SSH CONNECTION
        1 server = 1 SSH session cho toàn bộ quá trình scan
        """
        ssh_connection = None
        try:
            # 1. Tìm ComplianceResult pending
            compliance_result = self.db.query(ComplianceResult).filter(
                ComplianceResult.server_id == server.id,
                ComplianceResult.status == "pending"
            ).first()
            
            if not compliance_result:
                logging.warning(f"No pending compliance result found for server {server.hostname}")
                return

            # 2. Update status = running
            compliance_result.status = "running"
            self.dao.update(compliance_result)

            # 3. Lấy workload và rules của server
            workload = self.workload_service.dao.get_by_id(server.workload_id)
            if not workload:
                logging.warning(f"Server {server.hostname} không có workload")
                compliance_result.status = "failed"
                self.dao.update(compliance_result)
                return

            rules = self.db.query(Rule).filter(
                Rule.workload_id == workload.id,
                Rule.is_active == True
            ).all()

            if not rules:
                compliance_result.status = "completed"
                compliance_result.total_rules = 0
                self.dao.update(compliance_result)
                return

            # 4. OPTIMIZED: Tạo persistent SSH connection
            ssh_connection = self._create_persistent_ssh_connection(server)
            if not ssh_connection:
                raise Exception("Cannot establish SSH connection to server")

            # 5. Thực thi tất cả rules với persistent connection
            rule_results = self._execute_all_rules_with_persistent_connection(
                server, rules, ssh_connection, compliance_result.id
            )

            # 6. Bulk create rule results
            if rule_results:
                self.rule_result_dao.create_bulk(rule_results)

            # 7. Update final compliance result
            rules_passed = sum(1 for rr in rule_results if rr.status == "passed")
            rules_failed = len(rule_results) - rules_passed

            compliance_result.status = "completed"
            compliance_result.total_rules = len(rules)
            compliance_result.passed_rules = rules_passed
            compliance_result.failed_rules = rules_failed
            compliance_result.score = int((rules_passed / len(rules) * 100) if len(rules) > 0 else 0)
            
            self.dao.update(compliance_result)
            
            logging.info(f"Server {server.hostname} scan completed: {rules_passed}/{len(rules)} rules passed ({compliance_result.score}% score)")

        except Exception as e:
            logging.error(f"Error scanning server {server.hostname}: {str(e)}")
            try:
                if compliance_result:
                    compliance_result.status = "failed"
                    self.dao.update(compliance_result)
            except Exception as update_e:
                logging.error(f"Error updating failed status: {str(update_e)}")
        
        finally:
            # CRITICAL: Đóng SSH connection
            if ssh_connection:
                self._close_ssh_connection(ssh_connection)
                logging.info(f"Closed SSH connection to server {server.hostname}")

    def _create_persistent_ssh_connection(self, server: Server) -> Optional[Dict[str, Any]]:
        """Tạo persistent SSH connection sử dụng Ansible ControlPersist"""
        try:
            # Tạo unique control path cho server này
            control_path = f"/tmp/ansible-ssh-{server.ip_address}-{int(time.time())}"
            
            # Tạo inventory với ControlPersist
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
                    logging.error(f"Failed to establish SSH connection to {server.hostname}: {result.stderr}")
                    if os.path.exists(inventory_path):
                        os.unlink(inventory_path)
                    return None
                    
            except Exception as e:
                logging.error(f"Error testing SSH connection to {server.hostname}: {str(e)}")
                if os.path.exists(inventory_path):
                    os.unlink(inventory_path)
                return None
                
        except Exception as e:
            logging.error(f"Error creating persistent SSH connection to {server.hostname}: {str(e)}")
            return None

    def _execute_all_rules_with_persistent_connection(
        self, server: Server, rules: List[Rule], ssh_connection: Dict[str, Any], compliance_result_id: int
    ) -> List[RuleResult]:
        """Thực thi tất cả rules sử dụng persistent SSH connection"""
        all_rule_results = []
        inventory_path = ssh_connection["inventory_path"]
        
        for i, rule in enumerate(rules):
            try:
                start_time = time.time()
                
                # Lấy commands cho rule này
                commands = self.db.query(Command).filter(
                    Command.rule_id == rule.id,
                    Command.os_version == server.os_version,
                    Command.is_active == True
                ).all()

                if not commands:
                    # No commands for this OS version
                    rule_result = RuleResult(
                        compliance_result_id=compliance_result_id,
                        rule_id=rule.id,
                        rule_name=rule.name,
                        status="skipped",
                        message=f"Không có command nào cho OS {server.os_version}",
                        details="",
                        execution_time=0
                    )
                    all_rule_results.append(rule_result)
                    continue

                # Combine commands
                combined_command = " && ".join([cmd.command_text for cmd in commands])
                
                # Thực thi command sử dụng persistent connection
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
                logging.error(f"Error executing rule {rule.name} on server {server.hostname}: {str(e)}")
                
                # Tạo error result
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

    def _execute_command_with_persistent_connection(self, inventory_path: str, command: str) -> Dict[str, Any]:
        """Thực thi command sử dụng persistent SSH connection"""
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
            return {"success": False, "error": "Command execution timeout", "stdout": "", "stderr": ""}
        except Exception as e:
            return {"success": False, "error": f"Command execution error: {str(e)}", "stdout": "", "stderr": ""}

    def _close_ssh_connection(self, ssh_connection: Dict[str, Any]):
        """Đóng persistent SSH connection và cleanup resources"""
        try:
            inventory_path = ssh_connection.get("inventory_path")
            control_path = ssh_connection.get("control_path")
            server = ssh_connection.get("server")
            
            # Đóng ControlMaster connection
            if control_path and os.path.exists(control_path):
                try:
                    subprocess.run([
                        "ssh", "-o", f"ControlPath={control_path}",
                        "-O", "exit", f"{server.ssh_user}@{server.ip_address}"
                    ], capture_output=True, timeout=5)
                except Exception as e:
                    logging.debug(f"Error closing ControlMaster: {str(e)}")
                
                # Remove control path file
                try:
                    if os.path.exists(control_path):
                        os.unlink(control_path)
                except Exception as e:
                    logging.debug(f"Error removing control path: {str(e)}")
            
            # Cleanup inventory file
            if inventory_path and os.path.exists(inventory_path):
                try:
                    os.unlink(inventory_path)
                except Exception as e:
                    logging.debug(f"Error removing inventory file: {str(e)}")
            
            duration = time.time() - ssh_connection.get("established_at", time.time())
            logging.info(f"Closed SSH connection to {server.hostname} (duration: {duration:.1f}s)")
            
        except Exception as e:
            logging.error(f"Error closing SSH connection: {str(e)}")

    def get_compliance_status(self, compliance_id: int) -> Optional[Dict[str, Any]]:
        """Lấy trạng thái hiện tại của một compliance scan"""
        compliance_result = self.dao.get_by_id(compliance_id)
        if not compliance_result:
            return None
            
        server = self.server_dao.get_by_id(compliance_result.server_id)
        server_hostname = server.hostname if server else "Unknown"
            
        return {
            "id": compliance_result.id,
            "server_id": compliance_result.server_id,
            "server_hostname": server_hostname,
            "status": compliance_result.status,
            "progress": {
                "total_rules": compliance_result.total_rules,
                "passed_rules": compliance_result.passed_rules,
                "failed_rules": compliance_result.failed_rules,
                "score": compliance_result.score
            },
            "scan_date": compliance_result.scan_date.isoformat(),
            "updated_at": compliance_result.updated_at.isoformat()
        }
    
    def cancel_compliance_scan(self, compliance_id: int) -> bool:
        """Hủy một compliance scan đang chạy"""
        try:
            compliance_result = self.dao.get_by_id(compliance_id)
            if not compliance_result:
                return False
                
            if compliance_result.status not in ["running", "pending"]:
                return False
                
            compliance_result.status = "cancelled"
            self.dao.update(compliance_result)
            return True
            
        except Exception as e:
            logging.error(f"Error cancelling compliance scan {compliance_id}: {str(e)}")
            return False

    def get_server_compliance_history(self, server_id: int, limit: int = 10) -> List[ComplianceResultResponse]:
        """Lấy lịch sử compliance của một server"""
        try:
            results, _ = self.dao.search_compliance_results(server_id=server_id, skip=0, limit=limit)
            return [self._convert_to_response(result) for result in results]
        except Exception as e:
            logging.error(f"Error getting server compliance history: {str(e)}")
            return []

    def export_compliance_report(self, compliance_id: int) -> Optional[Dict[str, Any]]:
        """Export báo cáo compliance"""
        try:
            compliance_detail = self.get_compliance_result_detail(compliance_id)
            if not compliance_detail:
                return None
                
            report = {
                "scan_info": {
                    "id": compliance_detail.id,
                    "server_id": compliance_detail.server_id,
                    "server_hostname": compliance_detail.server_hostname,
                    "workload_name": compliance_detail.workload_name,
                    "scan_date": compliance_detail.scan_date.isoformat(),
                    "status": compliance_detail.status,
                    "score": compliance_detail.score
                },
                "summary": {
                    "total_rules": compliance_detail.total_rules,
                    "passed_rules": compliance_detail.passed_rules,
                    "failed_rules": compliance_detail.failed_rules,
                    "success_rate": f"{(compliance_detail.passed_rules / compliance_detail.total_rules * 100):.1f}%" if compliance_detail.total_rules > 0 else "0%"
                },
                "detailed_results": [
                    {
                        "rule_id": rr.rule_id,
                        "rule_name": rr.rule_name,
                        "status": rr.status,
                        "message": rr.message,
                        "details": rr.details,
                        "execution_time": rr.execution_time
                    } for rr in compliance_detail.rule_results
                ]
            }
            
            return report
            
        except Exception as e:
            logging.error(f"Error exporting compliance report {compliance_id}: {str(e)}")
            return None

    def _convert_to_response(self, compliance: ComplianceResult) -> ComplianceResultResponse:
        return ComplianceResultResponse(
            id=compliance.id,
            server_id=compliance.server_id,
            status=compliance.status,
            total_rules=compliance.total_rules,
            passed_rules=compliance.passed_rules,
            failed_rules=compliance.failed_rules,
            score=compliance.score,
            scan_date=compliance.scan_date,
            created_at=compliance.created_at,
            updated_at=compliance.updated_at
        )

    def _convert_rule_result_to_response(self, rule_result: RuleResult) -> RuleResultResponse:
        return RuleResultResponse(
            id=rule_result.id,
            compliance_result_id=rule_result.compliance_result_id,
            rule_id=rule_result.rule_id,
            rule_name=rule_result.rule_name,
            status=rule_result.status,
            message=rule_result.message,
            details=rule_result.details,
            execution_time=rule_result.execution_time,
            created_at=rule_result.created_at,
            updated_at=rule_result.updated_at
        )
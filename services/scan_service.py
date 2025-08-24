from ast import parse
import json
import time 
import logging
import os
import tempfile
import yaml 
import ansible_runner 
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from models.rule import Rule
from models.rule_result import RuleResult
from models.server import Server

from schemas.compliance import ComplianceScanRequest, ComplianceScanResponse
from services.command_service import CommandService
from services.compilance_result_service import ComplianceResultService
from services.rule_service import RuleService
from services.server_service import ServerService
from services.workload_service import WorkloadService

class ScanService: 
    def __init__(self, db: Session):
        self.db = db
        self.server_serivice = ServerService(db)
        self.compliance_result_service = ComplianceResultService(db)
        self.workload_service = WorkloadService(db)
        self.rule_service = RuleService(db)
        self.command_service = CommandService(db)
        # Timeout này sẽ được ansible-runner quản lý
        self.ansible_timeout = 30 

    def start_compliance_scan(self, scan_request : ComplianceScanRequest) -> ComplianceScanResponse:
        """
        co hai loai chinh: 
        1. quet toan bo server trong he thong
        2. quet nhung server co id trong danh sach truyen vao
        """
        try:
            server_ids = scan_request.server_ids if scan_request.server_ids else []
            logging.info(f"Starting compliance scan for {len(server_ids)} servers")
            if server_ids:
                return self.scan_specific_servers(scan_request)
            else: 
                return self.scan_all_servers(scan_request)
        except Exception as e:
            logging.error(f"Error starting compliance scan: {str(e)}")
            raise e

    def scan_all_servers(self, scan_request: ComplianceScanRequest) -> ComplianceScanResponse:

        total_servers = self.server_serivice.count_servers()
        started_scans = []

        skip = 0
        limit = scan_request.batch_size

        while skip < total_servers:
            servers = self.server_serivice.get_active_servers(skip=skip, limit=limit)
            if not servers:
                break
            
            batch_compliance = []
            for server in servers:
                try:
                    compliance_result = self.compliance_result_service.create_pending_result(server.id)
                    batch_compliance.append(compliance_result)
                    started_scans.append(compliance_result.id)
                except Exception as e:
                    logging.error(f"Error creating pending result for server {server.id}: {str(e)}")
                    continue
            
            if servers and batch_compliance: 
                self._process_compliance_scan_batches(servers, batch_compliance)
            
            skip += limit

        return ComplianceScanResponse(
            message=f"Đã bắt đầu quét {len(started_scans)} servers thành công",
            total_servers=len(started_scans),
            started_scans=started_scans
        )        
    def scan_specific_servers(self, scan_request: ComplianceScanRequest) -> ComplianceScanResponse:
        total_servers = len(scan_request.server_ids)
        started_scans = []

        index = 0
        while index < total_servers:
            batch_ids = scan_request.server_ids[index: index + scan_request.batch_size]
            servers = []
            batch_compliance = []
            
            for server_id in batch_ids:
                server = self.server_serivice.get_server_by_id(server_id)
                if server and server.status:
                    servers.append(server)
                    try:
                        compliance_result = self.compliance_result_service.create_pending_result(server.id)
                        batch_compliance.append(compliance_result)
                        started_scans.append(compliance_result.id)
                    except Exception as e:
                        logging.error(f"Error creating pending result for server {server.id}: {str(e)}")
                        continue
            
            if servers and batch_compliance: 
                self._process_compliance_scan_batches(servers, batch_compliance)
            
            index += scan_request.batch_size

        return ComplianceScanResponse(
            message=f"Đã bắt đầu quét {len(started_scans)} servers thành công",
            total_servers=len(started_scans),
            started_scans=started_scans
        )

    def _process_compliance_scan_batches(self, servers: List[Server], compliance_results: List[Any]):
        for server, compliance_result in zip(servers, compliance_results):
             self.scan_single_server(server, compliance_result)

    def scan_single_server(self, server: Server, compliance_result: Any):
        try:
            self.compliance_result_service.update_status(compliance_result.id, "running")
            workload = self.workload_service.get_workload_by_id(server.workload_id)

            if not workload:
                logging.warning(f"Server {server.hostname} không có workload")
                self.compliance_result_service.update_status(compliance_result.id, "failed", detail_error="Không có workload")
                return

            rules = self.rule_service.get_active_rule_by_workload(workload.id)
            if not rules:
                logging.warning(f"Workload {workload.name} không có rule nào được kích hoạt")
                self.compliance_result_service.update_status(compliance_result.id, "failed", detail_error="Không có rule nào được kích hoạt")
                return

            
            rule_results, error_message = self._execute_rules_with_ansible_runner(server, rules, compliance_result.id)
            
            if error_message:
                self.compliance_result_service.update_status(compliance_result.id, "failed", detail_error=error_message)
                return

            self.compliance_result_service.complete_result(compliance_result.id, rule_results, len(rules))
            logging.info(f"Server {server.hostname} scan completed successfully")

        except Exception as e:
            logging.error(f"Error scanning server {server.id}: {str(e)}")
            self.compliance_result_service.update_status(compliance_result.id, "failed", detail_error=str(e))


    def _execute_rules_with_ansible_runner(
    self, server: Server, rules: List[Rule], compliance_result_id: int
) -> (List[RuleResult], Optional[str]):
  
        all_rule_results = []
      
        rules_to_run = {} 

        playbook_tasks = []
        for rule in rules:
            start_time = time.time()
            command = self.command_service.get_command_for_rule_excecution(rule.id, server.os_version)

            if not command:
                all_rule_results.append(RuleResult(
                    compliance_result_id=compliance_result_id, rule_id=rule.id, rule_name=rule.name,
                    status="skipped", message=f"Không có command cho OS {server.os_version}", execution_time=0
                ))
                continue
            
            # Tạo một tên task duy nhất và có thể đoán được
            task_name = f"Execute rule ID {rule.id}: {rule.name}"
            rules_to_run[task_name] = {'rule': rule, 'start_time': start_time}
            
            playbook_tasks.append({
                'name': task_name, # Dùng tên task đã tạo
                'shell': command.command_text,
                'register': f"result_{rule.id}", # Vẫn giữ register để debug nếu cần, nhưng không dùng để ánh xạ
                'ignore_errors': True
            })

        if not playbook_tasks:
            return all_rule_results, None

        with tempfile.TemporaryDirectory() as private_data_dir:
            # ... (code tạo inventory và playbook giữ nguyên) ...
            inventory = { 'all': { 'hosts': { server.ip_address: {
                'ansible_user': server.ssh_user, 'ansible_password': server.ssh_password,
                'ansible_port': server.ssh_port,
                'ansible_ssh_common_args': '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
            }}}}
            inventory_path = os.path.join(private_data_dir, 'inventory.yml')
            with open(inventory_path, 'w') as f: yaml.dump(inventory, f)

            playbook = [{'hosts': 'all', 'gather_facts': False, 'tasks': playbook_tasks}]
            playbook_path = os.path.join(private_data_dir, 'scan_playbook.yml')
            with open(playbook_path, 'w') as f: yaml.dump(playbook, f)

            logging.info(f"Running single ansible-runner process for {len(playbook_tasks)} rules on {server.hostname}")
            runner = ansible_runner.run(
                private_data_dir=private_data_dir, playbook=playbook_path, inventory=inventory_path,
                quiet=True, cmdline=f'--timeout {self.ansible_timeout}'
            )
            
            all_events = list(runner.events)
            logging.debug("Ansible Runner Events JSON: %s", json.dumps(all_events, indent=2))
            
            if runner.status in ('failed', 'unreachable') or (runner.rc != 0 and not all_events):
                error_output = runner.stdout.read()
                full_error = f"Ansible run failed for {server.hostname}. Status: {runner.status}, RC: {runner.rc}. Output: {error_output}"
                logging.error(full_error)
                return [], f"Ansible connection failed: {error_output[:500] or 'Check logs for details'}"
        
            # Duyệt qua list sự kiện
            for event in all_events:
                if event['event'] in ('runner_on_ok', 'runner_on_failed'):
                    
                    # ---- SỬA LỖI LOGIC ÁNH XẠ Ở ĐÂY ----
                    task_name_from_event = event['event_data'].get('task')
                    if not task_name_from_event:
                        continue # Bỏ qua các event không có tên task

                    rule_info = rules_to_run.get(task_name_from_event)
                    if not rule_info:
                        # Log một cảnh báo nếu không tìm thấy, để dễ debug
                        logging.warning(f"Could not map event task '{task_name_from_event}' back to a rule.")
                        continue
                        
                    task_result = event['event_data']['res']
                    rule_obj = rule_info['rule']
                    execution_time = int(time.time() - rule_info['start_time'])

                    output = task_result.get('stdout', '')
                    error = task_result.get('stderr', '')
                    
                    # Logic đánh giá không đổi
                    is_passed = self._evaluate_rule_result(rule_obj, output)
                    
                    status = "passed"
                    message = "Rule execution successful"
                    
                    if task_result.get('rc', 1) != 0 or not is_passed:
                        status = "failed"
                        message = "Rule execution failed or parameters mismatch"
                    
                    details = output[:500] if status == "passed" else (error or output)[:500]

                    all_rule_results.append(RuleResult(
                        compliance_result_id=compliance_result_id,
                        rule_id=rule_obj.id,
                        rule_name=rule_obj.name,
                        status=status,
                        message=message,
                        details=details,
                        execution_time=execution_time
                    ))

        return all_rule_results, None
        
    def _evaluate_rule_result(self, rule: Rule, command_output: str) -> bool:
        """
        Đánh giá rule với parameters. Trả về True nếu passed, False nếu failed.
        """
        print("DEBUG - Command Output:", command_output)
        if not rule.parameters or not isinstance(rule.parameters, dict):
            # Nếu không có tham số, chỉ cần command thành công (đã kiểm tra rc ở hàm gọi)
            return True
        
        try:
            parsed_output = self._parse_output_values(command_output)
            return self._compare_with_parameters(rule.parameters, parsed_output)
        except Exception as e:
            logging.error(f"Error evaluating rule {rule.name}: {str(e)}")
            return False

    def _parse_output_values(self, output: str) -> Dict[str, Any]:
    
       
        parsed_data = {}
        clean_output = output.strip()
        if not clean_output:
            return parsed_data

        try:
            # 1. Thử phân tích dưới dạng Key-Value
            lines = [line.strip() for line in clean_output.splitlines() if line.strip()]
            if lines and '=' in clean_output:
                delimiter = '=' if all('=' in line for line in lines) else None
                if delimiter:
                    temp_dict = {
                        parts[0].strip(): parts[1].strip()
                        for line in lines
                        if len(parts := line.split(delimiter, 1)) == 2
                    }
                    if temp_dict:
                        parsed_data.update(temp_dict)
                        return parsed_data
            
            # 2. Thử phân tích dưới dạng các giá trị phân tách bằng dấu cách
            values = clean_output.split()
            if len(values) > 1:
                parsed_data["all_values"] = " ".join(values)
                for i, val in enumerate(values):
                    parsed_data[f"value_{i}"] = val
                return parsed_data
            
            # 3. Coi là một giá trị duy nhất
            parsed_data["single_value"] = clean_output
            return parsed_data
        except Exception as e:
            logging.warning(f"Could not parse command output. Error: {e}. Output: '{clean_output[:100]}'")
            parsed_data["parse_error"] = str(e)
            return parsed_data

    def _compare_with_parameters(self, parameters: Dict, parsed_output: Dict[str, Any]) -> bool:
        print("DEBUG - Rule Parameters:", parameters)
        print("DEBUG - Parsed Output for Comparison:", parsed_output)

       
        params_to_check = {k: v for k, v in parameters.items() if k not in ["docs", "note", "description"]}
        
      
        if not params_to_check:
            return True
            
        print("DEBUG - Parameters to Check:", params_to_check)
        
        expected_values = list(params_to_check.values())

        print("DEBUG - Expected Values:", expected_values)
        actual_values = []
        for key in parsed_output:
            actual_values.append(parsed_output[key])
        print("DEBUG - Actual Values:", actual_values)


       

        # Kiểm tra số lượng phần tử
        if len(actual_values) < len(expected_values):
            logging.debug(
                f"Value count mismatch: Not enough values in output. "
                f"Expected at least {len(expected_values)}, Got {len(actual_values)}"
            )
            return False
            
        # So sánh từng phần tử theo thứ tự
        # Chỉ so sánh số lượng phần tử có trong expected_values
        for i in range(len(expected_values)):
            if str(actual_values[i]).strip() != str(expected_values[i]).strip():
                logging.debug(
                    f"Value mismatch at index {i}: "
                    f"Expected '{expected_values[i]}', Got '{actual_values[i]}'"
                )
                return False
                
        logging.debug("All values matched in order. PASSED.")
        return True
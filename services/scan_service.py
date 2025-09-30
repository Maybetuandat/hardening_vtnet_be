from ast import parse
from collections import Counter
import json
import time 
import logging
import os
import tempfile
import yaml 
import ansible_runner 
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine
from dao.instance_dao import InstanceDAO
from models.rule import Rule
from models.rule_result import RuleResult
from models.instance import Instance

from models.user import User
from schemas.compliance_result import ComplianceScanRequest, ComplianceScanResponse

from services.compilance_result_service import ComplianceResultService
from services.rule_service import RuleService
from services.instance_service import InstanceService
from services.workload_service import WorkloadService

class ScanService: 
    def __init__(self, db: Session):
        self.db = db
        # Lưu thông tin kết nối database để tạo session mới cho mỗi thread
        self.db_engine = db.bind
        self.session_maker = sessionmaker(bind=self.db_engine)
        
        # Các service sẽ được khởi tạo trong mỗi thread với session riêng
        self.ansible_timeout = 30
        # Số luồng tối đa chạy đồng thời
        self.max_workers = 10
        self._thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        self._warm_up_threads()
        
    def _warm_up_threads(self):
        
        def dummy_task():
            time.sleep(0.01)  
            return "warmed"
        futures = [self._thread_pool.submit(dummy_task) for _ in range(self.max_workers)]
        for future in futures:
            future.result()
        
        logging.info(f"Thread pool warmed up with {self.max_workers} threads")
    def start_compliance_scan(self, scan_request : ComplianceScanRequest, current_user : User) -> ComplianceScanResponse:
        """
        co hai loai chinh: 
        1. quet toan bo server trong he thong
        2. quet nhung server co id trong danh sach truyen vao
        """
        try:
            if scan_request.server_ids :
                print("DEBUG - Scanning specific servers:", scan_request.server_ids)
                return self._scan_servers_by_batch(scan_request, specific_ids=scan_request.server_ids, current_user=current_user)
            else: 
                print("DEBUG - Scanning all active servers")
                return self._scan_servers_by_batch(scan_request, current_user=current_user)
        except Exception as e:
            logging.error(f"Error starting compliance scan: {str(e)}")
            raise e

    def _scan_servers_by_batch(self, scan_request: ComplianceScanRequest, specific_ids: Optional[List[int]] = None, current_user: Optional[User] = None) -> ComplianceScanResponse:
            instance_dao = InstanceDAO(self.db)
            
            print("DEBUG - Scan request batch size:", specific_ids)
            started_scans_count = 0 
            
            skip = 0
            limit = scan_request.batch_size 

            
            while True:
                instances_in_batch_objects = []
                if specific_ids:
                    current_batch_ids = specific_ids[skip: skip + limit]
                    if not current_batch_ids:
                        break 
                    
                    for instance_id in current_batch_ids:
                        instance = instance_dao.get_by_id(instance_id)
                        if instance:
                            instances_in_batch_objects.append(instance)
                else:
                    instances_in_batch_objects = instance_dao.get_instances(skip=skip, limit=limit, current_user_id=current_user.id , is_has_workload=True)
                    if not instances_in_batch_objects:
                        break

                if not instances_in_batch_objects:
                    break

                
                current_batch_data = []
                for instance in instances_in_batch_objects:
                    instance_dict = self.convert_server_model_to_dict(instance, current_user)
                    current_batch_data.append(instance_dict)

             
              
                # cau lenh nay co tac dung tach doi tuong ra khoi session hien tai
                self.db.expunge_all() 
                self.db.close() 

                
                if current_batch_data:
                    logging.info(f"Processing batch of {len(current_batch_data)} instances (offset={skip})")
                    # Gọi hàm xử lý đa luồng cho batch này và đợi nó hoàn thành
                    processed_in_batch = self._process_compliance_scan_batch_threaded(current_batch_data)
                    started_scans_count += processed_in_batch
                
                skip += limit 

               
                self.db = self.session_maker()


            return ComplianceScanResponse(
                message=f"Đã bắt đầu quá trình quét cho {started_scans_count} instance(s).",
                total_instances=started_scans_count,
                started_scans=[] 
            )

    def convert_server_dict_to_model(self, data: Dict[str, Any]):
        if not data:
            return None
        return Instance(**data)

    def convert_server_model_to_dict(self, server, current_user: Optional[User] = None) -> Dict[str, Any]:
        if not server:
            return {}
        return {
            "id": server.id,
            
            "name": server.name,
            "ssh_user": current_user.username if current_user else "",
            "ssh_password": current_user.ssh_password if current_user else "",
            "ssh_port": server.ssh_port,
            "workload_id": server.workload_id,
            "status": server.status,
            "created_at": server.created_at.isoformat() if server.created_at else None,
            "updated_at": server.updated_at.isoformat() if server.updated_at else None
        }
    def _process_compliance_scan_batch_threaded(self, batch_server_data: List[Dict[str, Any]]) -> int:  
        successful_scans_in_batch = 0
        future_to_server_data = {}
        for server_data in batch_server_data:
            future = self._thread_pool.submit(self._scan_single_server_threaded, server_data)
            future_to_server_data[future] = server_data
            logging.info(f"IMMEDIATE - Submitted task for {server_data['name']} to pre-warmed thread")
        
        
        for future in as_completed(future_to_server_data):
            server_data = future_to_server_data[future]
            try:
                future.result() 
                successful_scans_in_batch += 1
                logging.info(f"Instance {server_data['name']} scan completed successfully within batch.")
            except Exception as e:
                logging.error(f"Instance {server_data['name']} scan failed within batch: {str(e)}")
        
        return successful_scans_in_batch
    def _scan_single_server_threaded(self, server_data: Dict[str, Any]):
        
        thread_id = threading.current_thread().ident
        start_time = time.time()
        logging.info(f" THREAD {thread_id} STARTED IMMEDIATELY for {server_data['name']} at {start_time}")
        thread_session = self.session_maker()
        
        compliance_result_id = None 
        
        try:
            print(f"DEBUG - Thread {thread_id} scanning server: {server_data}")
            
            
            compliance_result_service = ComplianceResultService(thread_session)
            workload_service = WorkloadService(thread_session)
            rule_service = RuleService(thread_session)
            instance_service = InstanceService(thread_session)

            # tạo ra compliance result khi bắt đầu scan
            compliance_result = compliance_result_service.create_pending_result(server_data['id'], server_data['workload_id'])
            compliance_result_id = compliance_result.id 
            thread_session.commit()
            
            compliance_result_service.update_status(compliance_result_id, "running")
            thread_session.commit()

            # thực hiện lấy workload 
            workload = workload_service.get_workload_by_id(server_data['workload_id'])
            if not workload:
                logging.warning(f"Thread {thread_id}: Instance {server_data['name']} không có workload")
                compliance_result_service.update_status(compliance_result_id, "failed", detail_error="Không có workload")
                thread_session.commit()
                return
            # thực hiện lấy rule thuộc về workload 
            rules = rule_service.get_active_rule_by_workload(workload.id)
            print("Debug get rules in workload", rules)
            if not rules:
                logging.warning(f"Thread {thread_id}: Workload {workload.name} không có rule nào được kích hoạt")
                compliance_result_service.update_status(compliance_result_id, "failed", detail_error="Không có rule nào được kích hoạt")
                thread_session.commit()
                return

            rule_results, error_message = self._execute_rules_with_ansible_runner_threaded(
                server_data, rules, compliance_result_id,  thread_id
            )
            
            if error_message:
                compliance_result_service.update_status(compliance_result_id, "failed", detail_error=error_message)
                
                instance_service.update_status(server_data['id'], False)

                thread_session.commit()
                
                return

            compliance_result_service.complete_result(compliance_result_id, rule_results, len(rules))
            thread_session.commit()
            
            logging.info(f"Thread {thread_id}: Instance {server_data['name']} scan completed successfully")
            

        except Exception as e:
            thread_session.rollback()
            logging.error(f"Thread {thread_id}: Error scanning server {server_data['id']}: {str(e)}")
            if compliance_result_id:
                try:
                    temp_session_for_error = self.session_maker() 
                    temp_compliance_result_service = ComplianceResultService(temp_session_for_error)
                    temp_compliance_result_service.update_status(compliance_result_id, "failed", detail_error=str(e))
                    temp_session_for_error.commit()
                    temp_session_for_error.close()
                except Exception as update_e:
                    logging.error(f"Thread {thread_id}: Failed to update error status for server {server_data['id']}: {update_e}")
            raise 
        finally:
            thread_session.close()

    def _execute_rules_with_ansible_runner_threaded(
        self, server_data: Dict[str, Any], rules: List[Rule], compliance_result_id: int, 
         thread_id: int
    ) -> (List[RuleResult], Optional[str]): 
       
        all_rule_results = []
        rules_to_run = {}
        playbook_tasks = []

        print("Debug - Executing rules with Ansible Runner:", rules)
        logging.info(f"Thread {thread_id}: Preparing {len(rules)} rules for server {server_data['name']}")

        # Chuẩn bị playbook tasks
        for rule in rules:
            start_time = time.time()
            task_name = f"Execute rule ID {rule.id}: {rule.name}"
            rules_to_run[task_name] = {'rule': rule, 'start_time': start_time}
            
            playbook_tasks.append({
                'name': task_name,
                'shell': rule.command,
                'ignore_errors': True
            })

        if not playbook_tasks:
            return all_rule_results, None

        # thực hiện gen ra file playbook để thực hiện với ansible 
        with tempfile.TemporaryDirectory() as private_data_dir:
            inventory = { 'all': { 'hosts': { server_data['name']: {
                'ansible_user': server_data['ssh_user'], 'ansible_password': server_data['ssh_password'],
                'ansible_port': server_data['ssh_port'],
                'ansible_ssh_common_args': '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
            }}}}
            inventory_path = os.path.join(private_data_dir, 'inventory.yml')
            with open(inventory_path, 'w') as f: 
                yaml.dump(inventory, f)

            playbook = [{'hosts': 'all', 'gather_facts': False, 'tasks': playbook_tasks}]
            playbook_path = os.path.join(private_data_dir, 'scan_playbook.yml')
            with open(playbook_path, 'w') as f: 
                yaml.dump(playbook, f)

            logging.info(f"Thread {thread_id}: Running ansible-runner for {len(playbook_tasks)} rules on {server_data['name']}")
            runner = ansible_runner.run(
                private_data_dir=private_data_dir, 
                playbook=playbook_path, 
                inventory=inventory_path,
                quiet=True, 
                cmdline=f'--timeout {self.ansible_timeout}'
            )
            
            all_events = list(runner.events)
            
            if runner.status in ('failed', 'unreachable') or (runner.rc != 0 and not all_events):
                error_output = runner.stdout.read()
                full_error = f"Thread {thread_id}: Ansible run failed for {server_data['name']}. Status: {runner.status}, RC: {runner.rc}. Output: {error_output}"
                logging.error(full_error)
                return [], f"Ansible connection failed: {error_output[:500] or 'Check logs for details'}"
        
            # Xử lý kết quả
            for event in all_events:
                if event['event'] in ('runner_on_ok', 'runner_on_failed'):

                    print(f"DEBUG - Thread Event {thread_id} Event: {event}")  
                    task_name_from_event = event['event_data'].get('task')
                    if not task_name_from_event:
                        continue 

                    rule_info = rules_to_run.get(task_name_from_event)
                    if not rule_info:
                        logging.warning(f"Thread {thread_id}: Could not map event task '{task_name_from_event}' back to a rule.")
                        continue
                        
                    task_result = event['event_data']['res']
                    rule_obj = rule_info['rule']
                    execution_time = int(time.time() - rule_info['start_time'])

                    output = task_result.get('stdout', '')
                    error = task_result.get('stderr', '')

                    is_passed, parsed_output_dict = self._evaluate_rule_result(rule_obj, output)
                    status = "passed"
                    message = "Rule execution successful"
                    
                    if task_result.get('rc', 1) != 0 :
                        status = "failed"
                        message = "Rule execution failed"
                    if not is_passed:
                        status = "failed"
                        message = "Paramter mismatch "
                    details_error = None
                    if status == "failed" and  error:
                        details_error = error[:500]
                    

                    all_rule_results.append(RuleResult(
                        compliance_result_id=compliance_result_id,
                        rule_id=rule_obj.id,
                        
                        status=status,
                        message=message,
                        details_error=details_error,
                        
                        output=parsed_output_dict
                    ))

        
        return all_rule_results, None
        
    def _evaluate_rule_result(self, rule: Rule, command_output: str) -> tuple[bool, dict]:
       
        if not rule.parameters or not isinstance(rule.parameters, dict):
            return True, {} 
        
        try:
            parsed_output = self._parse_output_values(command_output)

            
            # is_passed là true nếu giá trị khớp, failed nếu giá trị sai
            is_passed = self._compare_with_parameters(rule.parameters, parsed_output)

            return is_passed, parsed_output

        except Exception as e:
            logging.error(f"Error evaluating rule {rule.name}: {str(e)}")
            return False, {"error": str(e)}

    def _parse_output_values(self, output: str) -> Dict[str, Any]:
      
        parsed_data = {}
        print(f"DEBUG - Raw command output: '{output}'")
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

    def _compare_with_parameters(self, parameters: Dict[str, Any], parsed_output: Dict[str, Any]) -> bool:
        print("DEBUG - Rule Parameters:", parameters)
        print("DEBUG - Parsed Output for Comparison:", parsed_output)

        # Remove excluded keys
        params_to_check = {k: v for k, v in parameters.items() if k not in ["docs", "note", "description"]}
        if not params_to_check:
            return True

        expected_values = [str(v).strip() for v in params_to_check.values()]
        actual_values = [str(v).strip() for v in parsed_output.values()]

        print("DEBUG - Expected Values:", expected_values)
        print("DEBUG - Actual Values:", actual_values)

        # Compare as multisets (ignore order, allow duplicates)
        if sorted(expected_values) != sorted(actual_values[:len(expected_values)]):
            logging.debug(
                f"Value mismatch: Expected {expected_values}, Got {actual_values}"
            )
            return False

        logging.debug("All values matched (ignoring keys & order). PASSED.")
        return True

import logging
import os
import tempfile
import time
import yaml
import ansible_runner
import re
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session
from dao.fix_request_dao import FixRequestDAO
from dao.rule_dao import RuleDAO
from dao.rule_result_dao import RuleResultDAO
from dao.instance_dao import InstanceDAO
from dao.compliance_result_dao import ComplianceDAO
from dao.fix_action_log_dao import FixActionLogDAO
from dao.user_dao import UserDAO
from models.fix_action_log import FixActionLog
from models.user import User
from schemas.fix_execution import ServerFixRequest, ServerFixResponse, SingleRuleFixResult
from schemas.fix_request import FixRequestResponse
from services.compilance_result_service import ComplianceResultService

class FixService:
    def __init__(self, db: Session, user_id: int = None, username: str = None, ip_address: str = None, user_agent: str = None):
        self.db = db
        self.rule_result_dao = RuleResultDAO(db)
        self.rule_dao = RuleDAO(db)
        self.instance_dao = InstanceDAO(db)
        self.compliance_dao = ComplianceDAO(db)
        self.fix_log_dao = FixActionLogDAO(db)
        self.ansible_timeout = 30
        self.compliance_result_service = ComplianceResultService(db)
        self.fix_request_dao = FixRequestDAO(db)
        self.user_dao = UserDAO(db)
        
        
        # User context for logging
        self.user_id = user_id
        self.username = username
        self.ip_address = ip_address
        self.user_agent = user_agent
    
    def fix_request_from_admin(self, request_id: int) -> ServerFixResponse:
        fix_request = self.fix_request_dao.get_by_id(request_id)
        request = ServerFixRequest(
            instance_id=fix_request.instance_id,
            rule_result_ids=[fix_request.rule_result_id]
        )
        
        user = self.user_dao.get_by_username(fix_request.created_by)
        self.user_id = user.id
        self.username = user.username
        return self.execute_server_fixes(request, user)
        

    def execute_server_fixes(self, request: ServerFixRequest, current_user: User) -> ServerFixResponse:
        try:
            instance = self.instance_dao.get_by_id(request.instance_id)
            if not instance:
                raise ValueError(f"Instance with ID {request.instance_id} not found")

            print("Debug user", current_user.username, current_user.id)
            # Validate and prepare fix data
            fix_data = self._prepare_fix_data(request.rule_result_ids, request.instance_id)
            
            print("is calling")
            if not fix_data["valid_fixes"]:
                return ServerFixResponse(
                    message="No valid fixes to execute",
                    instance_id=request.instance_id,
                    instance_ip=instance.name,
                    total_fixes=len(request.rule_result_ids),
                    successful_fixes=0,
                    failed_fixes=0,
                    skipped_fixes=len(request.rule_result_ids),
                    fix_details=fix_data["fix_details"]
                )
            
            execution_result = self._execute_grouped_fixes(instance, fix_data["valid_fixes"], current_user)
            
            fix_details = self._update_rule_results_from_execution(
                fix_data["valid_fixes"], 
                fix_data["fix_details"], 
                execution_result
            )
            
            # Count results
            successful_fixes = sum(1 for detail in fix_details if detail["status"] == "success")
            failed_fixes = sum(1 for detail in fix_details if detail["status"] == "failed")
            skipped_fixes = sum(1 for detail in fix_details if detail["status"] == "skipped")
            
            return ServerFixResponse(
                message=f"Instance fixes completed: {successful_fixes} successful, {failed_fixes} failed, {skipped_fixes} skipped",
                instance_id=request.instance_id,
                instance_ip=instance.name,
                total_fixes=len(request.rule_result_ids),
                successful_fixes=successful_fixes,
                failed_fixes=failed_fixes,
                skipped_fixes=skipped_fixes,
                fix_details=fix_details
            )
            
        except Exception as e:
            logging.error(f"Error executing server fixes for server {request.instance_id}: {str(e)}")
            raise e
    
    def _prepare_fix_data(self, rule_result_ids: List[int], instance_id: int) -> Dict[str, Any]:
        valid_fixes = []
        fix_details = []
        
        for rule_result_id in rule_result_ids:
            # Get rule result
            rule_result = self.rule_result_dao.get_by_id(rule_result_id)
            #if rule result not found
            if not rule_result:
                fix_details.append(SingleRuleFixResult(
                    rule_result_id=rule_result_id,
                    rule_name="Unknown",
                    fix_command=None,
                    status="skipped",
                    message="Rule result not found",
                    execution_output=None,
                    error_details=None
                ))
                continue
            
            # Verify rule result belongs to the correct instance
            compliance_result = self.compliance_dao.get_by_id(rule_result.compliance_result_id)
            if not compliance_result or compliance_result.instance_id != instance_id:
                fix_details.append(SingleRuleFixResult(
                    rule_result_id=rule_result_id,
                    rule_name="Unknown",
                    fix_command=None,
                    status="skipped",
                    message="Rule result does not belong to specified server",
                    execution_output=None,
                    error_details=None
                ))
                continue
            
            # Check if rule result status is failed
            if rule_result.status == "passed":
                fix_details.append(SingleRuleFixResult(
                    rule_result_id=rule_result_id,
                    rule_name="Unknown",
                    fix_command=None,
                    status="skipped",
                    message=f"Rule result status is '{rule_result.status}', no fix needed",
                    execution_output=None,
                    error_details=None
                ))
                continue
            
            # Get rule to get suggested_fix command
            rule = self.rule_dao.get_by_id(rule_result.rule_id)
            if not rule:
                fix_details.append(SingleRuleFixResult(
                    rule_result_id=rule_result_id,
                    rule_name="Unknown",
                    fix_command=None,
                    status="skipped",
                    message="Rule not found",
                    execution_output=None,
                    error_details=None
                ))
                continue
            
            if not rule.suggested_fix or not rule.suggested_fix.strip():
                fix_details.append(SingleRuleFixResult(
                    rule_result_id=rule_result_id,
                    rule_name=rule.name,
                    fix_command=None,
                    status="skipped",
                    message="No suggested fix available for this rule",
                    execution_output=None,
                    error_details=None
                ))
                continue
            

            print("Debug suggested fix", rule.suggested_fix)
            valid_fixes.append({
                "rule_result_id": rule_result_id,
                "compliance_result_id": compliance_result.id if compliance_result else None,
                "rule_result": rule_result,
                "rule": rule,
                "task_name": f"Fix rule {rule.name} (ID: {rule_result_id})",
                "fix_command": rule.suggested_fix.strip()
            })
            
            fix_details.append({
                "rule_result_id": rule_result_id,
                "rule_name": rule.name,
                "fix_command": rule.suggested_fix.strip(),
                "status": "pending",
                "message": "Pending execution",
                "execution_output": None,
                "error_details": None
            })
        
        return {
            "valid_fixes": valid_fixes,
            "fix_details": fix_details
        }

   
    def _generate_task_description(self, command: str, base_name: str, counter: int) -> str:
        """
        Tạo mô tả ngắn gọn cho task dựa trên command
        """
        # Các patterns phổ biến
        if 'cp ' in command and '.bak' in command:
            return f"{base_name} - Step {counter}: Backup configuration"
        elif 'sed -i' in command and '/d' in command:
            return f"{base_name} - Step {counter}: Remove old parameter"
        elif 'echo' in command and 'tee -a' in command:
            return f"{base_name} - Step {counter}: Add new parameter"
        elif 'sysctl -p' in command:
            return f"{base_name} - Step {counter}: Apply sysctl changes"
        elif 'sync' in command:
            return f"{base_name} - Step {counter}: Sync filesystem"
        elif 'drop_caches' in command:
            return f"{base_name} - Step {counter}: Drop system caches"
        else:
            # Cắt ngắn command nếu quá dài
            short_cmd = command[:50] + '...' if len(command) > 50 else command
            return f"{base_name} - Step {counter}: {short_cmd}"

    def _execute_grouped_fixes(self, instance, valid_fixes: List[Dict], current_user: User) -> Dict[str, Any]:
        try:
            with tempfile.TemporaryDirectory() as private_data_dir:
                # Tạo inventory
                inventory = {
                    'all': {
                        'hosts': {
                            instance.name: {
                                'ansible_user': current_user.username,
                                'ansible_password': current_user.ssh_password,
                                'ansible_port': instance.ssh_port,
                                'ansible_ssh_common_args': '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=30',
                                'ansible_become': True,
                                'ansible_become_method': 'sudo',
                                'ansible_become_password': current_user.ssh_password,
                                'ansible_become_user': 'root',
                                'ansible_connection': 'ssh',
                                'ansible_ssh_timeout': 30
                            }
                        }
                    }
                }
                
                inventory_path = os.path.join(private_data_dir, 'inventory.yml')
                with open(inventory_path, 'w') as f:
                    yaml.dump(inventory, f)
                
                # Tạo playbook tasks - phân tách từng fix thành nhiều tasks
                playbook_tasks = []
                
                for fix_data in valid_fixes:
                    fix_command = fix_data["fix_command"]
                    base_task_name = fix_data["task_name"]

                    print("Debug fix command", fix_command)

                    task = {
                        'name': base_task_name,
                        'shell': fix_command,
                        'ignore_errors': True,
                        'become': True,
                        'register': f"result_{fix_data['rule_result_id']}"
                    }
                    playbook_tasks.append(task)
                    
                    # Thêm task verification (chạy rule command để kiểm tra)
                    verify_task = {
                        'name': f"{base_task_name} - Verification",
                        'shell': fix_data["rule"].command,
                        'ignore_errors': True,
                        'become': True,
                        'register': f"verify_{fix_data['rule_result_id']}"
                    }
                    playbook_tasks.append(verify_task)
                
                playbook = [{
                    'hosts': 'all',
                    'gather_facts': False,
                    'become': True,
                    'tasks': playbook_tasks
                }]
                
                playbook_path = os.path.join(private_data_dir, 'grouped_fix_playbook.yml')
                with open(playbook_path, 'w') as f:
                    yaml.dump(playbook, f, default_flow_style=False, allow_unicode=True)
                
                print(f"Executing {len(valid_fixes)} fixes with {len(playbook_tasks)} total tasks on {instance.name}")
                
                runner = ansible_runner.run(
                    private_data_dir=private_data_dir,
                    playbook=playbook_path,
                    inventory=inventory_path,
                    quiet=True,
                    cmdline=f'--timeout {self.ansible_timeout} --forks 1'
                )
                
                task_results = {}
                
                print("Debug runner events", runner.events)
                for event in runner.events:
                    if event['event'] in ('runner_on_ok', 'runner_on_failed'):
                        task_name = event['event_data'].get('task')
                        if task_name:
                            task_result = event['event_data']['res']
                            task_results[task_name] = {
                                "success": event['event'] == 'runner_on_ok' and task_result.get('rc', 1) == 0,
                                "stdout": task_result.get('stdout', ''),
                                "stderr": task_result.get('stderr', ''),
                                "rc": task_result.get('rc', 1),
                                "failed": task_result.get('failed', False),
                                "changed": task_result.get('changed', False)
                            }
                            print("Debug task name")
                            print(f"Task '{task_name}' executed with rc={task_results[task_name]['rc']}")
                
                return {
                    "overall_success": runner.status == 'successful',
                    "task_results": task_results,
                    "runner_status": runner.status,
                    "runner_rc": runner.rc
                }
                
        except Exception as e:
            logging.error(f"Error executing grouped fixes on {instance.name}: {str(e)}")
            return {
                "overall_success": False,
                "task_results": {},
                "error": str(e)
            }

    def _update_rule_results_from_execution(self, valid_fixes: List[Dict], fix_details: List[Dict], execution_result: Dict) -> List[Dict]:
        task_results = execution_result.get("task_results", {})
        
        for i, detail in enumerate(fix_details):
            if detail["status"] != "pending":
                continue 
            
            # Find corresponding valid_fix with fix_detail 
            valid_fix = None
            for fix_data in valid_fixes:
                if fix_data["rule_result_id"] == detail["rule_result_id"]:
                    valid_fix = fix_data
                    break
            
            if not valid_fix:
                continue
            
            # Tìm kết quả verification task
            verify_task_name = f"{valid_fix['task_name']} - Verification"
            verify_result = task_results.get(verify_task_name)
            
            if not verify_result:
                # Không tìm thấy kết quả verification
                fix_details[i].update({
                    "status": "failed",
                    "message": "No verification result found",
                    "error_details": "Verification task may not have executed"
                })
                
                self._log_fix_action(
                    valid_fix, 
                    "failed", 
                    "failed", 
                    error_message="No verification result found"
                )
                continue
            
            # Kiểm tra kết quả verification
            if verify_result["success"] and verify_result["rc"] == 0:
                # Fix thành công - cập nhật rule result
                rule_result = valid_fix["rule_result"]
                old_status = rule_result.status
                
                rule_result.status = "passed"
                rule_result.message = "Fixed successfully"
                rule_result.output = self._parse_output_values(verify_result["stdout"])
                rule_result.details_error = None
                self.rule_result_dao.update(rule_result)
                self.compliance_result_service.calculate_score(valid_fix["compliance_result_id"])
                
                fix_details[i].update({
                    "status": "success",
                    "message": "Fix executed successfully and verified",
                    "execution_output": verify_result["stdout"]
                })
                
                self._log_fix_action(
                    valid_fix, 
                    old_status, 
                    "passed",
                    execution_output=verify_result["stdout"]
                )
                
            else:
                # Fix thất bại hoặc verification không pass
                error_details = verify_result["stderr"] or f"Verification failed with return code {verify_result['rc']}"
                fix_details[i].update({
                    "status": "failed",
                    "message": "Fix execution or verification failed",
                    "execution_output": verify_result["stdout"],
                    "error_details": error_details
                })
                
                self._log_fix_action(
                    valid_fix, 
                    valid_fix["rule_result"].status, 
                    valid_fix["rule_result"].status,
                    execution_output=verify_result["stdout"],
                    error_message=error_details,
                    is_success=False
                )
        
        return fix_details
    
    def _log_fix_action(
        self, 
        valid_fix: Dict, 
        old_status: str, 
        new_status: str, 
        execution_output: Optional[str] = None,
        error_message: Optional[str] = None,
        is_success: bool = True
    ):
        try:
            if not self.user_id or not self.username:
                logging.warning("Cannot create fix log: User information not available")
                return

            log_entry = FixActionLog(
                user_id=self.user_id,
                username=self.username,
                rule_result_id=valid_fix["rule_result_id"],
                compliance_result_id=valid_fix["compliance_result_id"],
                rule_name=valid_fix["rule"].name,
                old_status=old_status,
                new_status=new_status,
                command=valid_fix["fix_command"],
                execution_output=execution_output,
                error_message=error_message,
                is_success=is_success,
                ip_address=self.ip_address if self.ip_address else "unknown",
                user_agent=self.user_agent if self.user_agent else "unknown"
            )

            self.fix_log_dao.create(log_entry)
            print(f"Fix action logged: {self.username} updated rule {valid_fix['rule_result_id']} from {old_status} to {new_status}")
            
        except Exception as log_error:
            logging.warning(f"Failed to create fix action log: {str(log_error)}")
    
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
                for i, val in enumerate(values):
                    parsed_data[f"value_{i}"] = val
                return parsed_data
            
            # 3. Coi là một giá trị duy nhất
            parsed_data["single_value"] = clean_output
            return parsed_data
        except Exception as e:
            logging.warning(f"Could not parse command output. Error: {e}")
            parsed_data["parse_error"] = str(e)
            return parsed_data
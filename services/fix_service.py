import logging
import os
import tempfile
import time
import yaml
import ansible_runner
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session
from dao.rule_dao import RuleDAO
from dao.rule_result_dao import RuleResultDAO
from dao.server_dao import ServerDAO
from dao.compliance_result_dao import ComplianceDAO
from schemas.fix_execution import ServerFixRequest, ServerFixResponse, SingleRuleFixResult
from services.compilance_result_service import ComplianceResultService



class FixService:
    def __init__(self, db: Session):
        self.db = db
        self.rule_result_dao = RuleResultDAO(db)
        self.rule_dao = RuleDAO(db)
        self.server_dao = ServerDAO(db)
        self.compliance_dao = ComplianceDAO(db)
        self.ansible_timeout = 30
        self.compliance_result_service = ComplianceResultService(db)
        
    def execute_server_fixes(self, request: ServerFixRequest) -> ServerFixResponse:
        try:
            server = self.server_dao.get_by_id(request.server_id)
            if not server:
                raise ValueError(f"Server with ID {request.server_id} not found")
            
            # Validate and prepare fix data
            fix_data = self._prepare_fix_data(request.rule_result_ids, request.server_id)
            
            if not fix_data["valid_fixes"]:
                return ServerFixResponse(
                    message="No valid fixes to execute",
                    server_id=request.server_id,
                    server_ip=server.ip_address,
                    total_fixes=len(request.rule_result_ids),
                    successful_fixes=0,
                    failed_fixes=0,
                    skipped_fixes=len(request.rule_result_ids),
                    fix_details=fix_data["fix_details"]
                )
            
            
            
            execution_result = self._execute_grouped_fixes(server, fix_data["valid_fixes"])
            
            
            
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
                message=f"Server fixes completed: {successful_fixes} successful, {failed_fixes} failed, {skipped_fixes} skipped",
                server_id=request.server_id,
                server_ip=server.ip_address,
                total_fixes=len(request.rule_result_ids),
                successful_fixes=successful_fixes,
                failed_fixes=failed_fixes,
                skipped_fixes=skipped_fixes,
                fix_details=fix_details
            )
            
        except Exception as e:
            logging.error(f"Error executing server fixes for server {request.server_id}: {str(e)}")
            raise e
    
    def _prepare_fix_data(self, rule_result_ids: List[int], server_id: int) -> Dict[str, Any]:
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
            
            # Verify rule result belongs to the correct server
            compliance_result = self.compliance_dao.get_by_id(rule_result.compliance_result_id)
            if not compliance_result or compliance_result.server_id != server_id:
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
    
   
    def _execute_grouped_fixes(self, server, valid_fixes: List[Dict]) -> Dict[str, Any]:
        try:
            with tempfile.TemporaryDirectory() as private_data_dir:
                # Tạo inventory với cấu hình rõ ràng hơn
                inventory = {
                    'all': {
                        'hosts': {
                            server.ip_address: {
                                'ansible_user': server.ssh_user,
                                'ansible_password': server.ssh_password,
                                'ansible_port': server.ssh_port,
                                'ansible_ssh_common_args': '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=30',
                                'ansible_become': True,
                                'ansible_become_method': 'sudo',
                                'ansible_become_password': server.ssh_password, 
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
                
                # Tạo playbook tasks
                playbook_tasks = []
                for fix_data in valid_fixes:
                    task = {
                        'name': fix_data["task_name"],
                        'shell': fix_data["fix_command"] + ' && ' + fix_data["rule"].command,
                        'ignore_errors': True,
                        'become': True,
                        'register': f"result_{fix_data['rule_result_id']}"
                    }
                    playbook_tasks.append(task)
                
                playbook = [{
                    'hosts': 'all',
                    'gather_facts': False,
                    'become': True,
                    'tasks': playbook_tasks
                }]
                
                playbook_path = os.path.join(private_data_dir, 'grouped_fix_playbook.yml')
                with open(playbook_path, 'w') as f:
                    yaml.dump(playbook, f)
                
                print(f"Executing {len(valid_fixes)} grouped fixes on {server.ip_address}")
                
                
                runner = ansible_runner.run(
                    private_data_dir=private_data_dir,
                    playbook=playbook_path,
                    inventory=inventory_path,
                    quiet=True,
                    
                    cmdline=f'--timeout {self.ansible_timeout} --forks 1'
                    
                )
                
                
                task_results = {}
                
             
                
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

                            print(f"Task '{task_name}' executed with result: {task_results[task_name]}")
                
                return {
                    "overall_success": runner.status == 'successful',
                    "task_results": task_results,
                    "runner_status": runner.status,
                    "runner_rc": runner.rc
                }
                
        except Exception as e:
            logging.error(f"Error executing grouped fixes on {server.ip_address}: {str(e)}")
            return {
                "overall_success": False,
                "task_results": {},
                "error": str(e)
            }

    def _update_rule_results_from_execution(self, valid_fixes: List[Dict], fix_details: List[Dict], execution_result: Dict) -> List[Dict]:
        task_results = execution_result.get("task_results", {})
        
        # print("Debug: Task results from execution:", task_results)
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
            
            task_name = valid_fix["task_name"]
            task_result = task_results.get(task_name)
            
            if not task_result:
                # Task didn't execute or no result found
                fix_details[i].update({
                    "status": "failed",
                    "message": "No execution result found for this fix",
                    "error_details": "Task may not have executed"
                })
                continue
            
            if task_result["success"]:
                # Fix was successful - update rule result in database
                rule_result = valid_fix["rule_result"]
                rule_result.status = "passed"
                rule_result.message = "Fixed successfully"
                rule_result.output = self._parse_output_values(task_result["stdout"])
                rule_result.details_error = None
                self.rule_result_dao.update(rule_result)
                self.compliance_result_service.calculate_score(valid_fix["compliance_result_id"])
                fix_details[i].update({
                    "status": "success",
                    "message": "Fix executed successfully and rule result updated to passed",
                    "execution_output": task_result["stdout"]
                })
                
            else:
                # Fix failed
                error_details = task_result["stderr"] or f"Command failed with return code {task_result['rc']}"
                fix_details[i].update({
                    "status": "failed",
                    "message": "Fix execution failed",
                    "execution_output": task_result["stdout"],
                    "error_details": error_details
                })
        
        return fix_details
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
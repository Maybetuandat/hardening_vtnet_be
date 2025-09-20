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


class FixService:
    def __init__(self, db: Session):
        self.db = db
        self.rule_result_dao = RuleResultDAO(db)
        self.rule_dao = RuleDAO(db)
        self.server_dao = ServerDAO(db)
        self.compliance_dao = ComplianceDAO(db)
        self.ansible_timeout = 30
        
    def execute_server_fixes(self, request: ServerFixRequest) -> ServerFixResponse:
        """Execute multiple fixes for a single server using one playbook"""
        try:
            # Get server info
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
            
            # Execute fixes using single playbook
            execution_result = self._execute_grouped_fixes(server, fix_data["valid_fixes"])
            
            # Update rule results based on execution results
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
        """Prepare and validate fix data for the given rule results"""
        valid_fixes = []
        fix_details = []
        
        for rule_result_id in rule_result_ids:
            # Get rule result
            rule_result = self.rule_result_dao.get_by_id(rule_result_id)
            if not rule_result:
                fix_details.append({
                    "rule_result_id": rule_result_id,
                    "rule_name": "Unknown",
                    "fix_command": None,
                    "status": "skipped",
                    "message": "Rule result not found",
                    "execution_output": None,
                    "error_details": None
                })
                continue
            
            # Verify rule result belongs to the correct server
            compliance_result = self.compliance_dao.get_by_id(rule_result.compliance_result_id)
            if not compliance_result or compliance_result.server_id != server_id:
                fix_details.append({
                    "rule_result_id": rule_result_id,
                    "rule_name": "Unknown",
                    "fix_command": None,
                    "status": "skipped",
                    "message": "Rule result does not belong to specified server",
                    "execution_output": None,
                    "error_details": None
                })
                continue
            
            # Check if rule result status is failed
            if rule_result.status != "failed":
                fix_details.append({
                    "rule_result_id": rule_result_id,
                    "rule_name": "Unknown",
                    "fix_command": None,
                    "status": "skipped",
                    "message": f"Rule result status is '{rule_result.status}', no fix needed",
                    "execution_output": None,
                    "error_details": None
                })
                continue
            
            # Get rule to get suggested_fix command
            rule = self.rule_dao.get_by_id(rule_result.rule_id)
            if not rule:
                fix_details.append({
                    "rule_result_id": rule_result_id,
                    "rule_name": "Unknown",
                    "fix_command": None,
                    "status": "skipped",
                    "message": "Rule not found",
                    "execution_output": None,
                    "error_details": None
                })
                continue
            
            if not rule.suggested_fix or not rule.suggested_fix.strip():
                fix_details.append({
                    "rule_result_id": rule_result_id,
                    "rule_name": rule.name,
                    "fix_command": None,
                    "status": "skipped",
                    "message": "No suggested fix available for this rule",
                    "execution_output": None,
                    "error_details": None
                })
                continue
            
            # Valid fix - add to list
            valid_fixes.append({
                "rule_result_id": rule_result_id,
                "rule_result": rule_result,
                "rule": rule,
                "task_name": f"Fix rule {rule.name} (ID: {rule_result_id})",
                "fix_command": rule.suggested_fix.strip()
            })
            
            # Add placeholder for valid fix (will be updated after execution)
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
        """Execute all fixes in a single playbook"""
        try:
            with tempfile.TemporaryDirectory() as private_data_dir:
                # Create inventory
                inventory = {
                    'all': {
                        'hosts': {
                            server.ip_address: {
                                'ansible_user': server.ssh_user,
                                'ansible_password': server.ssh_password,
                                'ansible_port': server.ssh_port,
                                'ansible_ssh_common_args': '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
                            }
                        }
                    }
                }
                
                inventory_path = os.path.join(private_data_dir, 'inventory.yml')
                with open(inventory_path, 'w') as f:
                    yaml.dump(inventory, f)
                
                # Create playbook tasks for all fixes
                playbook_tasks = []
                for fix_data in valid_fixes:
                    playbook_tasks.append({
                        'name': fix_data["task_name"],
                        'shell': fix_data["fix_command"],
                        'ignore_errors': True  # Continue with other fixes even if one fails
                    })
                
                playbook = [{
                    'hosts': 'all',
                    'gather_facts': False,
                    'tasks': playbook_tasks
                }]
                
                playbook_path = os.path.join(private_data_dir, 'grouped_fix_playbook.yml')
                with open(playbook_path, 'w') as f:
                    yaml.dump(playbook, f)
                
                # Run ansible
                logging.info(f"Executing {len(valid_fixes)} grouped fixes on {server.ip_address}")
                runner = ansible_runner.run(
                    private_data_dir=private_data_dir,
                    playbook=playbook_path,
                    inventory=inventory_path,
                    quiet=True,
                    cmdline=f'--timeout {self.ansible_timeout}'
                )
                
                # Process results from all events
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
                                "rc": task_result.get('rc', 1)
                            }
                
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
        """Update rule results and fix details based on execution results"""
        task_results = execution_result.get("task_results", {})
        
        # Update fix_details for valid fixes based on execution results
        for i, detail in enumerate(fix_details):
            if detail["status"] != "pending":
                continue  # Skip already processed (skipped) items
            
            # Find corresponding valid fix
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
                rule_result.details_error = None
                self.rule_result_dao.update(rule_result)
                
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
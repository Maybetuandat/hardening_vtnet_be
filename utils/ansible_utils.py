# utils/ansible_utils.py
import asyncio
import json
import tempfile
import os
import yaml
from typing import Dict, Any, List, Optional
import subprocess
import re
from datetime import datetime


class AnsibleExecutor:
    """Utility class for executing Ansible commands and playbooks"""
    
    @staticmethod
    def create_inventory(servers: List[Dict[str, Any]], ssh_key_path: str) -> str:
        """
        Tạo Ansible inventory file từ danh sách servers
        """
        inventory_content = "[targets]\n"
        
        for server in servers:
            inventory_content += (
                f"{server['ip_address']} "
                f"ansible_ssh_port={server.get('ssh_port', 22)} "
                f"ansible_ssh_private_key_file={ssh_key_path} "
                f"ansible_ssh_user=root "
                f"ansible_host={server['ip_address']}\n"
            )
        
        # Tạo file tạm thời
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(inventory_content)
            return f.name
    
    @staticmethod
    def create_playbook(tasks: List[Dict[str, Any]], gather_facts: bool = False) -> str:
        """
        Tạo Ansible playbook từ danh sách tasks
        """
        playbook_content = {
            'name': 'Security Compliance Check',
            'hosts': 'targets',
            'gather_facts': gather_facts,
            'tasks': tasks
        }
        
        playbook_yaml = yaml.dump([playbook_content], default_flow_style=False)
        
        # Tạo file tạm thời
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(playbook_yaml)
            return f.name
    
    @staticmethod
    async def execute_playbook(
        inventory_path: str, 
        playbook_path: str, 
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Thực thi Ansible playbook
        """
        cmd = [
            'ansible-playbook',
            '-i', inventory_path,
            playbook_path,
            '--ssh-common-args="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"',
            '-v'  # Verbose output
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            return {
                "return_code": process.returncode,
                "stdout": stdout.decode('utf-8'),
                "stderr": stderr.decode('utf-8'),
                "success": process.returncode == 0
            }
            
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return {
                "return_code": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "success": False
            }
        except Exception as e:
            return {
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False
            }
    
    @staticmethod
    def parse_ansible_output(output: str) -> List[Dict[str, Any]]:
        """
        Parse Ansible output to extract task results
        """
        results = []
        
        # Simple regex patterns to extract results
        # This is a basic implementation - you might need more sophisticated parsing
        
        # Look for task execution results
        task_pattern = r'TASK \[(.*?)\].*?(?=TASK|\Z)'
        tasks = re.findall(task_pattern, output, re.DOTALL)
        
        for task in tasks:
            # Extract task result information
            if 'ok:' in task:
                status = 'ok'
            elif 'failed:' in task:
                status = 'failed'
            elif 'changed:' in task:
                status = 'changed'
            elif 'skipped:' in task:
                status = 'skipped'
            else:
                status = 'unknown'
            
            results.append({
                'task': task.split(']')[0] if ']' in task else 'unknown',
                'status': status,
                'output': task.strip()
            })
        
        return results
    
    @staticmethod
    def cleanup_temp_files(*file_paths: str):
        """
        Xóa các file tạm thời
        """
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass  # Ignore cleanup errors


class TaskGenerator:
    """Utility class for generating Ansible tasks from commands"""
    
    @staticmethod
    def generate_shell_task(command: str, task_name: str = None) -> Dict[str, Any]:
        """
        Tạo Ansible shell task từ command string
        """
        if not task_name:
            task_name = f"Execute: {command[:50]}..."
        
        return {
            'name': task_name,
            'shell': command,
            'register': 'command_result',
            'ignore_errors': True
        }
    
    @staticmethod
    def generate_file_check_task(file_path: str, check_type: str = "exists") -> Dict[str, Any]:
        """
        Tạo task kiểm tra file
        """
        task_name = f"Check file {file_path} {check_type}"
        
        if check_type == "exists":
            return {
                'name': task_name,
                'stat': {'path': file_path},
                'register': 'file_result'
            }
        elif check_type == "permissions":
            return {
                'name': task_name,
                'shell': f"ls -la {file_path}",
                'register': 'permission_result',
                'ignore_errors': True
            }
        elif check_type == "content":
            return {
                'name': task_name,
                'shell': f"cat {file_path}",
                'register': 'content_result',
                'ignore_errors': True
            }
    
    @staticmethod
    def generate_service_check_task(service_name: str) -> Dict[str, Any]:
        """
        Tạo task kiểm tra service
        """
        return {
            'name': f"Check service {service_name}",
            'shell': f"systemctl is-active {service_name}",
            'register': 'service_result',
            'ignore_errors': True
        }
    
    @staticmethod
    def generate_package_check_task(package_name: str, os_type: str = "centos") -> Dict[str, Any]:
        """
        Tạo task kiểm tra package
        """
        if os_type.lower() in ['centos', 'redhat', 'rhel']:
            command = f"rpm -qa | grep {package_name}"
        elif os_type.lower() in ['ubuntu', 'debian']:
            command = f"dpkg -l | grep {package_name}"
        else:
            command = f"which {package_name}"
        
        return {
            'name': f"Check package {package_name}",
            'shell': command,
            'register': 'package_result',
            'ignore_errors': True
        }
    
    @staticmethod
    def generate_user_check_task(username: str) -> Dict[str, Any]:
        """
        Tạo task kiểm tra user
        """
        return {
            'name': f"Check user {username}",
            'shell': f"id {username}",
            'register': 'user_result',
            'ignore_errors': True
        }
    
    @staticmethod
    def generate_network_check_task(port: int, protocol: str = "tcp") -> Dict[str, Any]:
        """
        Tạo task kiểm tra network port
        """
        return {
            'name': f"Check {protocol} port {port}",
            'shell': f"netstat -tuln | grep :{port}",
            'register': 'network_result',
            'ignore_errors': True
        }
    
    @staticmethod
    def generate_security_task(rule_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tạo task kiểm tra security dựa trên rule type
        """
        if rule_type == "password_policy":
            return {
                'name': 'Check password policy',
                'shell': 'cat /etc/login.defs | grep -E "(PASS_MAX_DAYS|PASS_MIN_DAYS|PASS_WARN_AGE)"',
                'register': 'password_policy_result',
                'ignore_errors': True
            }
        elif rule_type == "ssh_config":
            return {
                'name': 'Check SSH configuration',
                'shell': 'sshd -T | grep -E "(permitrootlogin|passwordauthentication|protocol)"',
                'register': 'ssh_config_result',
                'ignore_errors': True
            }
        elif rule_type == "firewall":
            return {
                'name': 'Check firewall status',
                'shell': 'systemctl is-active iptables || systemctl is-active firewalld || ufw status',
                'register': 'firewall_result',
                'ignore_errors': True
            }
        elif rule_type == "file_permissions":
            file_path = parameters.get('file_path', '/etc/passwd')
            return {
                'name': f'Check file permissions for {file_path}',
                'shell': f'ls -la {file_path}',
                'register': 'file_permission_result',
                'ignore_errors': True
            }
        else:
            # Generic command
            command = parameters.get('command', 'echo "No command specified"')
            return TaskGenerator.generate_shell_task(command, f"Security check: {rule_type}")


class ResultParser:
    """Utility class for parsing and comparing results"""
    
    @staticmethod
    def parse_command_output(output: str, output_type: str = "text") -> Any:
        """
        Parse command output based on type
        """
        if output_type == "json":
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return None
        elif output_type == "numeric":
            try:
                # Extract first number from output
                numbers = re.findall(r'-?\d+\.?\d*', output)
                return float(numbers[0]) if numbers else None
            except (ValueError, IndexError):
                return None
        elif output_type == "boolean":
            # Check for common boolean indicators
            output_lower = output.lower().strip()
            if output_lower in ['true', 'yes', '1', 'enabled', 'active', 'running']:
                return True
            elif output_lower in ['false', 'no', '0', 'disabled', 'inactive', 'stopped']:
                return False
            return None
        else:
            return output.strip()
    
    @staticmethod
    def compare_values(actual: Any, expected: Any, comparison_type: str = "equals") -> Dict[str, Any]:
        """
        So sánh giá trị actual với expected
        """
        try:
            if comparison_type == "equals":
                passed = actual == expected
                message = f"Expected: {expected}, Actual: {actual}"
            elif comparison_type == "contains":
                passed = str(expected) in str(actual)
                message = f"Expected to contain: {expected}, Actual: {actual}"
            elif comparison_type == "greater_than":
                passed = float(actual) > float(expected)
                message = f"Expected > {expected}, Actual: {actual}"
            elif comparison_type == "less_than":
                passed = float(actual) < float(expected)
                message = f"Expected < {expected}, Actual: {actual}"
            elif comparison_type == "regex":
                passed = bool(re.search(str(expected), str(actual)))
                message = f"Expected pattern: {expected}, Actual: {actual}"
            elif comparison_type == "not_equals":
                passed = actual != expected
                message = f"Expected not: {expected}, Actual: {actual}"
            elif comparison_type == "range":
                # Expected should be a dict with min and max
                if isinstance(expected, dict):
                    min_val = expected.get('min')
                    max_val = expected.get('max')
                    val = float(actual)
                    passed = True
                    if min_val is not None and val < min_val:
                        passed = False
                    if max_val is not None and val > max_val:
                        passed = False
                    message = f"Expected range: {min_val}-{max_val}, Actual: {actual}"
                else:
                    passed = False
                    message = f"Invalid range format: {expected}"
            else:
                passed = False
                message = f"Unknown comparison type: {comparison_type}"
            
            return {
                "passed": passed,
                "message": message,
                "actual": actual,
                "expected": expected,
                "comparison_type": comparison_type
            }
            
        except Exception as e:
            return {
                "passed": False,
                "message": f"Comparison error: {str(e)}",
                "actual": actual,
                "expected": expected,
                "comparison_type": comparison_type
            }
    
    @staticmethod
    def extract_ansible_facts(ansible_output: str) -> Dict[str, Any]:
        """
        Trích xuất facts từ Ansible output
        """
        facts = {}
        
        # Look for gathered facts in output
        if "ansible_facts" in ansible_output:
            try:
                # Try to parse JSON facts
                import re
                facts_match = re.search(r'"ansible_facts":\s*({.*?})', ansible_output, re.DOTALL)
                if facts_match:
                    facts_json = facts_match.group(1)
                    facts = json.loads(facts_json)
            except:
                pass
        
        return facts
    
    @staticmethod
    def extract_task_results(ansible_output: str) -> List[Dict[str, Any]]:
        """
        Trích xuất kết quả các task từ Ansible output
        """
        results = []
        
        # Split by TASK sections
        task_sections = re.split(r'TASK \[.*?\]', ansible_output)
        
        for section in task_sections[1:]:  # Skip first empty section
            task_result = {
                "status": "unknown",
                "stdout": "",
                "stderr": "",
                "return_code": None,
                "changed": False,
                "failed": False
            }
            
            # Parse task result
            if "ok:" in section:
                task_result["status"] = "ok"
            elif "changed:" in section:
                task_result["status"] = "changed"
                task_result["changed"] = True
            elif "failed:" in section:
                task_result["status"] = "failed"
                task_result["failed"] = True
            elif "skipped:" in section:
                task_result["status"] = "skipped"
            
            # Extract stdout/stderr if present
            stdout_match = re.search(r'"stdout":\s*"([^"]*)"', section)
            if stdout_match:
                task_result["stdout"] = stdout_match.group(1)
            
            stderr_match = re.search(r'"stderr":\s*"([^"]*)"', section)
            if stderr_match:
                task_result["stderr"] = stderr_match.group(1)
            
            # Extract return code
            rc_match = re.search(r'"rc":\s*(\d+)', section)
            if rc_match:
                task_result["return_code"] = int(rc_match.group(1))
            
            results.append(task_result)
        
        return results


class SecurityRuleEngine:
    """Engine for processing security rules and generating appropriate checks"""
    
    @staticmethod
    def generate_tasks_for_rule(rule: Dict[str, Any], os_type: str) -> List[Dict[str, Any]]:
        """
        Tạo danh sách Ansible tasks cho một rule
        """
        tasks = []
        rule_name = rule.get('name', 'Unknown Rule')
        parameters = rule.get('parameters', {})
        
        # Generate tasks based on rule type or category
        if 'ssh' in rule_name.lower():
            tasks.extend(SecurityRuleEngine._generate_ssh_tasks(parameters))
        elif 'password' in rule_name.lower():
            tasks.extend(SecurityRuleEngine._generate_password_tasks(parameters))
        elif 'firewall' in rule_name.lower():
            tasks.extend(SecurityRuleEngine._generate_firewall_tasks(parameters, os_type))
        elif 'file' in rule_name.lower() and 'permission' in rule_name.lower():
            tasks.extend(SecurityRuleEngine._generate_file_permission_tasks(parameters))
        elif 'service' in rule_name.lower():
            tasks.extend(SecurityRuleEngine._generate_service_tasks(parameters))
        else:
            # Generic command-based rule
            command = parameters.get('command')
            if command:
                tasks.append(TaskGenerator.generate_shell_task(command, rule_name))
        
        return tasks
    
    @staticmethod
    def _generate_ssh_tasks(parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate SSH-related security tasks"""
        return [
            {
                'name': 'Check SSH root login setting',
                'shell': 'sshd -T | grep permitrootlogin',
                'register': 'ssh_root_login',
                'ignore_errors': True
            },
            {
                'name': 'Check SSH password authentication',
                'shell': 'sshd -T | grep passwordauthentication',
                'register': 'ssh_password_auth',
                'ignore_errors': True
            },
            {
                'name': 'Check SSH protocol version',
                'shell': 'sshd -T | grep protocol',
                'register': 'ssh_protocol',
                'ignore_errors': True
            }
        ]
    
    @staticmethod
    def _generate_password_tasks(parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate password policy tasks"""
        return [
            {
                'name': 'Check password aging settings',
                'shell': 'grep -E "^(PASS_MAX_DAYS|PASS_MIN_DAYS|PASS_WARN_AGE)" /etc/login.defs',
                'register': 'password_aging',
                'ignore_errors': True
            },
            {
                'name': 'Check password complexity',
                'shell': 'grep -E "minlen|dcredit|ucredit|lcredit|ocredit" /etc/security/pwquality.conf',
                'register': 'password_complexity',
                'ignore_errors': True
            }
        ]
    
    @staticmethod
    def _generate_firewall_tasks(parameters: Dict[str, Any], os_type: str) -> List[Dict[str, Any]]:
        """Generate firewall-related tasks"""
        tasks = []
        
        if os_type.lower() in ['centos', 'redhat', 'rhel']:
            tasks.extend([
                {
                    'name': 'Check firewalld status',
                    'shell': 'systemctl is-active firewalld',
                    'register': 'firewalld_status',
                    'ignore_errors': True
                },
                {
                    'name': 'Check iptables status',
                    'shell': 'systemctl is-active iptables',
                    'register': 'iptables_status',
                    'ignore_errors': True
                }
            ])
        elif os_type.lower() in ['ubuntu', 'debian']:
            tasks.extend([
                {
                    'name': 'Check ufw status',
                    'shell': 'ufw status',
                    'register': 'ufw_status',
                    'ignore_errors': True
                },
                {
                    'name': 'Check iptables rules',
                    'shell': 'iptables -L',
                    'register': 'iptables_rules',
                    'ignore_errors': True
                }
            ])
        
        return tasks
    
    @staticmethod
    def _generate_file_permission_tasks(parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate file permission check tasks"""
        files_to_check = parameters.get('files', ['/etc/passwd', '/etc/shadow', '/etc/group'])
        tasks = []
        
        for file_path in files_to_check:
            tasks.append({
                'name': f'Check permissions for {file_path}',
                'shell': f'ls -la {file_path}',
                'register': f'file_perm_{file_path.replace("/", "_").replace(".", "_")}',
                'ignore_errors': True
            })
        
        return tasks
    
    @staticmethod
    def _generate_service_tasks(parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate service check tasks"""
        services = parameters.get('services', [])
        tasks = []
        
        for service in services:
            tasks.append({
                'name': f'Check service {service}',
                'shell': f'systemctl is-active {service}',
                'register': f'service_{service}',
                'ignore_errors': True
            })
        
        return tasks
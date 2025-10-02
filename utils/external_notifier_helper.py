
import logging
from typing import Optional
from utils.external_notifier_worker import ExternalNotifierWorker

logger = logging.getLogger(__name__)


def send_external_notification(
    topic: str,
    title: str,
    message: str,
    priority: str = "normal",
    metadata: Optional[dict] = None
) -> bool:
    """
    Send notification to external chat system
    
    Args:
        topic: Category (e.g., 'rule_change', 'compliance', 'alert')
        title: Short title
        message: Full message content
        priority: 'low', 'normal', 'high', 'urgent'
        metadata: Additional tracking data
        
    Returns:
        bool: True if queued successfully
    """
    try:
        worker = ExternalNotifierWorker.get_instance()
        
        result = worker.send_message(
            topic=topic,
            title=title,
            message=message,
            priority=priority,
            metadata=metadata
        )
        
        if result:
            logger.debug(f"✅ Notification queued: {topic} - {title}")
        else:
            logger.warning(f"⚠️ Failed to queue: {topic} - {title}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error sending notification: {e}", exc_info=True)
        return False


def notify_rule_change_request(
    requester_username: str,
    action: str,
    rule_name: str,
    workload_name: str,
    request_id: int,
    priority: str = "normal"
) -> bool:
    """
    Send notification for new rule change request
    
    Args:
        requester_username: Who made the request
        action: 'create' or 'update'
        rule_name: Name of the rule
        workload_name: Name of the workload
        request_id: Request ID
        priority: Priority level
        
    Returns:
        bool: Success status
        
    Example:
        notify_rule_change_request(
            requester_username="john_doe",
            action="update",
            rule_name="Check CPU Usage",
            workload_name="Production Servers",
            request_id=123,
            priority="normal"
        )
    """
    title = f"New Rule {action.title()} Request"
    message = (
        f"{requester_username} requests to {action} "
        f"rule '{rule_name}' in workload '{workload_name}'"
    )
    
    return send_external_notification(
        topic="rule_change",
        title=title,
        message=message,
        priority=priority,
        metadata={
            "request_id": request_id,
            "action": action,
            "requester": requester_username,
            "rule_name": rule_name,
            "workload_name": workload_name
        }
    )


def notify_rule_change_result(
    admin_username: str,
    result: str,
    requester_username: str,
    action: str,
    rule_name: str,
    workload_name: str,
    admin_note: Optional[str] = None,
    priority: str = "normal"
) -> bool:
    """
    Send notification for rule change approval/rejection
    
    Args:
        admin_username: Admin who processed
        result: 'approved' or 'rejected'
        requester_username: Original requester
        action: 'create' or 'update'
        rule_name: Name of the rule
        workload_name: Name of the workload
        admin_note: Optional admin note
        priority: Priority level
        
    Returns:
        bool: Success status
        
    Example:
        notify_rule_change_result(
            admin_username="admin_alice",
            result="approved",
            requester_username="john_doe",
            action="update",
            rule_name="Check CPU Usage",
            workload_name="Production Servers",
            priority="normal"
        )
    """
    icon = "✅" if result == "approved" else "❌"
    title = f"{icon} Rule Change Request {result.title()}"
    
    message = (
        f"Admin {admin_username} {result} {requester_username}'s request "
        f"to {action} rule '{rule_name}' in workload '{workload_name}'"
    )
    
    if admin_note and result == "rejected":
        message += f"\nReason: {admin_note}"
    
    return send_external_notification(
        topic="rule_change",
        title=title,
        message=message,
        priority=priority,
        metadata={
            "result": result,
            "admin": admin_username,
            "requester": requester_username,
            "action": action,
            "rule_name": rule_name,
            "workload_name": workload_name,
            "admin_note": admin_note
        }
    )


def notify_compliance_completed(
    workload_name: str,
    total_rules: int,
    passed: int,
    failed: int,
    duration_seconds: float,
    priority: str = "normal"
) -> bool:
    """
    Send notification for compliance check completion
    
    Args:
        workload_name: Workload checked
        total_rules: Total rules
        passed: Rules passed
        failed: Rules failed
        duration_seconds: Check duration
        priority: Priority level
        
    Returns:
        bool: Success status
    """
    title = f"Compliance Check Completed: {workload_name}"
    message = (
        f"Workload '{workload_name}' compliance check finished\n"
        f"Results: {passed}/{total_rules} passed, {failed} failed\n"
        f"Duration: {duration_seconds:.1f}s"
    )
    
    # Auto adjust priority based on failure rate
    if total_rules > 0:
        failure_rate = failed / total_rules
        if failure_rate > 0.5:
            priority = "high"
        elif failure_rate > 0.8:
            priority = "urgent"
    
    return send_external_notification(
        topic="compliance",
        title=title,
        message=message,
        priority=priority,
        metadata={
            "workload_name": workload_name,
            "total_rules": total_rules,
            "passed": passed,
            "failed": failed,
            "duration_seconds": duration_seconds,
            "failure_rate": failed / total_rules if total_rules > 0 else 0
        }
    )


def get_notifier_stats() -> dict:
    """
    Get statistics from notifier worker
    
    Returns:
        dict: Stats including sent/failed counts, buffer size
        
    Example:
        >>> stats = get_notifier_stats()
        >>> print(stats)
        {
            'total_sent': 42,
            'total_failed': 2,
            'total_buffered': 44,
            'is_running': True,
            'buffer_size': 0
        }
    """
    try:
        worker = ExternalNotifierWorker.get_instance()
        return worker.get_stats()
    except Exception as e:
        logger.error(f"❌ Error getting stats: {e}")
        return {
            'total_sent': 0,
            'total_failed': 0,
            'total_buffered': 0,
            'is_running': False,
            'buffer_size': 0,
            'error': str(e)
        }
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List
from datetime import datetime


class MessagePriority(str, Enum):
    """Message priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class ExternalChatMessage:
    """
    Single chat message
    
    Attributes:
        topic: Message category (e.g., 'rule_change', 'compliance', 'alert')
        title: Short message title
        message: Full message content
        priority: Priority level (low/normal/high/urgent)
        metadata: Additional data for tracking
        timestamp: Message creation time
    """
    topic: str
    title: str
    message: str
    priority: MessagePriority = MessagePriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        """String representation"""
        return f"[{self.priority.value.upper()}] {self.topic}: {self.title}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'topic': self.topic,
            'title': self.title,
            'message': self.message,
            'priority': self.priority.value,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class MessageBatch:
    """
    Batch of messages for bulk sending
    
    Attributes:
        messages: List of chat messages
        batch_id: Unique batch identifier
        created_at: Batch creation time
    """
    messages: List[ExternalChatMessage] = field(default_factory=list)
    batch_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_message(self, message: ExternalChatMessage):
        """Add message to batch"""
        self.messages.append(message)
    
    def size(self) -> int:
        """Get number of messages in batch"""
        return len(self.messages)
    
    def is_empty(self) -> bool:
        """Check if batch is empty"""
        return len(self.messages) == 0
    
    def __str__(self) -> str:
        """String representation"""
        return f"MessageBatch(id={self.batch_id}, size={self.size()})"
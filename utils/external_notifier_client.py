

import logging
import json
from typing import List, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.external_notifier_config import ExternalNotifierConfig
from utils.external_notifier_models import ExternalChatMessage

logger = logging.getLogger(__name__)


class ExternalNotifierClient:
    """
    HTTP client for sending messages to external chat system
    
    Features:
    - Automatic retry with exponential backoff
    - Connection pooling
    - Timeout handling
    - Batch sending support
    
    Usage:
        client = ExternalNotifierClient(config)
        success, failed = client.send_batch(messages)
        client.close()
    """
    
    def __init__(self, config: ExternalNotifierConfig):
        """
        Initialize HTTP client
        
        Args:
            config: Notifier configuration
        """
        self.config = config
        
        # Create session with retry strategy
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,  # Total number of retries
            backoff_factor=1,  # Wait 1, 2, 4 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these status codes
            allowed_methods=["POST"]  # Only retry POST requests
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            "Authorization": f"Bearer {self.config.auth_token}",
            "Content-Type": "application/json"
        })
        
        logger.info("✅ External notifier client initialized")
    
    def send_single(self, message: ExternalChatMessage) -> bool:
        """
        Send single message to external chat API
        
        Args:
            message: Message to send
            
        Returns:
            bool: True if sent successfully
        """
        try:
            # Format message similar to Go implementation
            formatted_message = self._format_message(message)
            
            # Prepare payload matching Go's structure
            payload = {
                "channelid": self.config.channel_id,
                "message": formatted_message
            }
            
            # Send POST request
            response = self.session.post(
                url=self.config.api_url,
                json=payload,
                timeout=10  # 10 second timeout
            )
            
            # Check response
            if response.status_code in [200, 201, 204]:
                logger.debug(f"✅ Message sent: {message.topic} - {message.title}")
                return True
            else:
                logger.warning(
                    f"⚠️ Failed to send message. "
                    f"Status: {response.status_code}, "
                    f"Response: {response.text[:200]}"
                )
                return False
                
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout sending message: {message.topic} - {message.title}")
            return False
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"🔌 Connection error: {e}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error sending message: {e}", exc_info=True)
            return False
    
    def send_batch(self, messages: List[ExternalChatMessage]) -> Tuple[int, int]:
        """
        Send batch of messages
        
        Args:
            messages: List of messages to send
            
        Returns:
            Tuple[int, int]: (success_count, failure_count)
        """
        if not messages:
            return 0, 0
        
        success_count = 0
        failure_count = 0
        
        logger.info(f"📤 Sending batch of {len(messages)} messages...")
        
        for message in messages:
            try:
                if self.send_single(message):
                    success_count += 1
                else:
                    failure_count += 1
                    
            except Exception as e:
                logger.error(f"❌ Error processing message: {e}")
                failure_count += 1
        
        logger.info(
            f"✅ Batch completed: {success_count} sent, {failure_count} failed"
        )
        
        return success_count, failure_count
    
    def _format_message(self, message: ExternalChatMessage) -> str:
        """
        Format message for external chat system
        
        Matches Go format: [TOPIC] TITLE: MESSAGE
        
        Args:
            message: Message object
            
        Returns:
            str: Formatted message string
        """
        # Priority emoji mapping
        priority_emoji = {
            "low": "ℹ️",
            "normal": "📝",
            "high": "⚠️",
            "urgent": "🚨"
        }
        
        emoji = priority_emoji.get(message.priority.value, "📝")
        
        # Format: [TOPIC] TITLE: MESSAGE
        formatted = f"{emoji} [{message.topic.upper()}] {message.title}: {message.message}"
        
        # Add metadata if present and relevant
        if message.metadata:
            # Only add specific metadata that's useful in chat
            useful_metadata = []
            
            if "request_id" in message.metadata:
                useful_metadata.append(f"ID: {message.metadata['request_id']}")
            
            if "workload_name" in message.metadata:
                useful_metadata.append(f"Workload: {message.metadata['workload_name']}")
            
            if useful_metadata:
                formatted += f"\n({', '.join(useful_metadata)})"
        
        return formatted
    
    def close(self):
        """Close HTTP session"""
        if self.session:
            self.session.close()
            logger.info("🔒 External notifier client closed")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.close()
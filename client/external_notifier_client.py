# utils/external_notifier_client.py

import logging
import json
from typing import List, Tuple
import httpx

from config.external_notifier_config import ExternalNotifierConfig
from schemas.external_notifier_models import ExternalChatMessage


logger = logging.getLogger(__name__)


class ExternalNotifierClient:
    """
    HTTP client for sending messages to external chat system
    
    Uses httpx with HTTP/2 support and curl User-Agent to bypass server restrictions
    """
    
    def __init__(self, config: ExternalNotifierConfig):
        """
        Initialize HTTP client
        
        Args:
            config: Notifier configuration
        """
        self.config = config
        
        # Create httpx client with HTTP/2 support
        self.client = httpx.Client(http2=True, timeout=10.0)
        
        # Set default headers with curl User-Agent to bypass blocking
        self.client.headers.update({
            "Authorization": f"Bearer {self.config.auth_token}",
            "Content-Type": "application/json",
            "User-Agent": "curl/7.81.0",  # Fake curl User-Agent
            "Accept": "*/*"
        })
        
        logger.info("✅ External notifier client initialized")
        logger.info(f"   Using HTTP/2 with curl User-Agent")
        logger.info(f"   API URL: {self.config.api_url}")
        logger.info(f"   Channel ID: {self.config.channel_id}")
    
    def send_single(self, message: ExternalChatMessage) -> bool:
        """
        Send single message to external chat API
        
        Args:
            message: Message to send
            
        Returns:
            bool: True if sent successfully
        """
        try:
            formatted_message = self._format_message(message)
            
            payload = {
                "channel_id": self.config.channel_id,
                "message": formatted_message
            }
            
            logger.info(f"📤 Sending: {message.topic} - {message.title}")
            
            response = self.client.post(
                url=self.config.api_url,
                json=payload
            )
            
            if response.status_code in [200, 201, 204]:
                logger.info(f"✅ Message sent successfully (HTTP/{response.http_version})")
                return True
            else:
                logger.error(f"❌ Failed to send message")
                logger.error(f"   Status: {response.status_code}")
                logger.error(f"   Response: {response.text[:200]}")
                return False
                
        except httpx.TimeoutException:
            logger.error(f"⏱️ Timeout sending message: {message.topic} - {message.title}")
            return False
            
        except httpx.ConnectError as e:
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
            useful_metadata = []
            
            if "request_id" in message.metadata:
                useful_metadata.append(f"ID: {message.metadata['request_id']}")
            
            if "workload_name" in message.metadata:
                useful_metadata.append(f"Workload: {message.metadata['workload_name']}")
            
            if useful_metadata:
                formatted += f"\n({', '.join(useful_metadata)})"
        
        return formatted
    
    def close(self):
        """Close HTTP client"""
        if self.client:
            self.client.close()
            logger.info("🔒 External notifier client closed")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.close()
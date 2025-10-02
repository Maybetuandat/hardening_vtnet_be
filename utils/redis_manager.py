
import json
import redis
import logging
from typing import Dict, Any, Callable, Optional
from datetime import datetime

from config.setting_redis import get_redis_settings



logger = logging.getLogger(__name__)


class RedisPubSubManager:
    """Simple Redis Pub/Sub Manager"""
    
    def __init__(self):
        """Initialize Redis Pub/Sub Manager"""
        self.settings = get_redis_settings()
        
        # Create Redis connection
        self.redis_client = redis.from_url(
            self.settings.get_redis_url(),
            decode_responses=True
        )
        
        # Create separate PubSub instance for subscriber
        self.pubsub = self.redis_client.pubsub()
        
        logger.info(f"✅ Connected to Redis at {self.settings.REDIS_HOST}:{self.settings.REDIS_PORT}")
    
    # ==================== PUBLISHER ====================
    
    def publish_scan_request(self, data: Dict[str, Any]) -> int:
        """
        Publish scan request message
        
        Args:
            data: Scan request data (dict)
            
        Returns:
            Number of subscribers that received the message
        """
        try:
            message = {
                "timestamp": datetime.now().isoformat(),
                "type": "scan_request",
                "data": data
            }
            
            message_json = json.dumps(message)
            
            # Publish to channel
            num_subscribers = self.redis_client.publish(
                self.settings.REDIS_CHANNEL_SCAN_REQUEST,
                message_json
            )
            
            logger.info(f"📤 Published SCAN request to {num_subscribers} subscribers")
            logger.debug(f"Message: {message_json}")
            
            return num_subscribers
            
        except Exception as e:
            logger.error(f"❌ Error publishing scan request: {e}")
            raise
    
    def publish_scan_response(self, data: Dict[str, Any]) -> int:
        """
        Publish scan response message
        
        Args:
            data: Scan response data (dict)
            
        Returns:
            Number of subscribers that received the message
        """
        try:
            message = {
                "timestamp": datetime.now().isoformat(),
                "type": "scan_response",
                "data": data
            }
            
            message_json = json.dumps(message)
            
            num_subscribers = self.redis_client.publish(
                self.settings.REDIS_CHANNEL_SCAN_RESPONSE,
                message_json
            )
            
            logger.info(f"📤 Published SCAN response to {num_subscribers} subscribers")
            
            return num_subscribers
            
        except Exception as e:
            logger.error(f"❌ Error publishing scan response: {e}")
            raise
    
    def publish_fix_request(self, data: Dict[str, Any]) -> int:
        """Publish fix request message"""
        try:
            message = {
                "timestamp": datetime.now().isoformat(),
                "type": "fix_request",
                "data": data
            }
            
            message_json = json.dumps(message)
            
            num_subscribers = self.redis_client.publish(
                self.settings.REDIS_CHANNEL_FIX_REQUEST,
                message_json
            )
            
            logger.info(f"📤 Published FIX request to {num_subscribers} subscribers")
            
            return num_subscribers
            
        except Exception as e:
            logger.error(f"❌ Error publishing fix request: {e}")
            raise
    
    def publish_fix_response(self, data: Dict[str, Any]) -> int:
        """Publish fix response message"""
        try:
            message = {
                "timestamp": datetime.now().isoformat(),
                "type": "fix_response",
                "data": data
            }
            
            message_json = json.dumps(message)
            
            num_subscribers = self.redis_client.publish(
                self.settings.REDIS_CHANNEL_FIX_RESPONSE,
                message_json
            )
            
            logger.info(f"📤 Published FIX response to {num_subscribers} subscribers")
            
            return num_subscribers
            
        except Exception as e:
            logger.error(f"❌ Error publishing fix response: {e}")
            raise
    
    # ==================== SUBSCRIBER ====================
    
    def subscribe_scan_requests(self):
        """Subscribe to scan request channel"""
        self.pubsub.subscribe(self.settings.REDIS_CHANNEL_SCAN_REQUEST)
        logger.info(f"📡 Subscribed to {self.settings.REDIS_CHANNEL_SCAN_REQUEST}")
    
    def subscribe_scan_responses(self):
        """Subscribe to scan response channel"""
        self.pubsub.subscribe(self.settings.REDIS_CHANNEL_SCAN_RESPONSE)
        logger.info(f"📡 Subscribed to {self.settings.REDIS_CHANNEL_SCAN_RESPONSE}")
    
    def subscribe_fix_requests(self):
        """Subscribe to fix request channel"""
        self.pubsub.subscribe(self.settings.REDIS_CHANNEL_FIX_REQUEST)
        logger.info(f"📡 Subscribed to {self.settings.REDIS_CHANNEL_FIX_REQUEST}")
    
    def subscribe_fix_responses(self):
        """Subscribe to fix response channel"""
        self.pubsub.subscribe(self.settings.REDIS_CHANNEL_FIX_RESPONSE)
        logger.info(f"📡 Subscribed to {self.settings.REDIS_CHANNEL_FIX_RESPONSE}")
    
    def listen_for_messages(self, callback: Optional[Callable] = None):
        """
        Listen for messages from subscribed channels
        
        Args:
            callback: Optional callback function to handle messages
                     Signature: callback(channel: str, message: dict)
        
        Yields:
            Parsed message data
        """
        logger.info("👂 Listening for messages...")
        
        try:
            for message in self.pubsub.listen():
                # Skip subscription confirmation messages
                if message["type"] == "subscribe":
                    logger.info(f"✅ Successfully subscribed to {message['channel']}")
                    continue
                
                # Process actual messages
                if message["type"] == "message":
                    try:
                        channel = message["channel"]
                        data = json.loads(message["data"])
                        
                        logger.info(f"📥 Received message on {channel}")
                        logger.debug(f"Message content: {data}")
                        
                        # Call callback if provided
                        if callback:
                            callback(channel, data)
                        
                        yield {
                            "channel": channel,
                            "message": data
                        }
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Failed to parse message: {e}")
                        logger.error(f"Raw data: {message['data']}")
                    except Exception as e:
                        logger.error(f"❌ Error processing message: {e}")
                        
        except KeyboardInterrupt:
            logger.info("⏹️ Stopping message listener...")
            self.close()
        except Exception as e:
            logger.error(f"❌ Error in message listener: {e}")
            raise
    
    # ==================== UTILITY ====================
    
    def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            return self.redis_client.ping()
        except Exception as e:
            logger.error(f"❌ Redis health check failed: {e}")
            return False
    
    def close(self):
        """Close Redis connections"""
        try:
            self.pubsub.close()
            self.redis_client.close()
            logger.info("🔌 Redis connections closed")
        except Exception as e:
            logger.error(f"❌ Error closing connections: {e}")


# ==================== SINGLETON INSTANCE ====================

_pubsub_manager_instance = None

def get_pubsub_manager() -> RedisPubSubManager:
    """Get singleton instance of RedisPubSubManager"""
    global _pubsub_manager_instance
    
    if _pubsub_manager_instance is None:
        _pubsub_manager_instance = RedisPubSubManager()
    
    return _pubsub_manager_instance
"""
WebSocket Reliability Service
Implements Phase 2.4 of Production Roadmap
"""
import asyncio
import json
from typing import Dict, List, Set, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import logging
from collections import deque

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types"""
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    DATA = "data"
    HEARTBEAT = "heartbeat"
    ACK = "ack"
    ERROR = "error"


class ConnectionState(str, Enum):
    """WebSocket connection state"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class WebSocketMessage:
    """WebSocket message structure"""
    
    def __init__(
        self,
        message_type: MessageType,
        data: Dict,
        message_id: Optional[str] = None,
        requires_ack: bool = False
    ):
        self.message_id = message_id or self._generate_id()
        self.message_type = message_type
        self.data = data
        self.requires_ack = requires_ack
        self.timestamp = datetime.utcnow()
        self.retry_count = 0
        self.acknowledged = False
    
    def _generate_id(self) -> str:
        """Generate unique message ID"""
        import uuid
        return str(uuid.uuid4())
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'message_id': self.message_id,
            'type': self.message_type.value,
            'data': self.data,
            'timestamp': self.timestamp.isoformat()
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


class MessageQueue:
    """Message queue with persistence"""
    
    def __init__(self, max_size: int = 1000):
        self.queue: deque = deque(maxlen=max_size)
        self.pending_acks: Dict[str, WebSocketMessage] = {}
        self.max_size = max_size
    
    def enqueue(self, message: WebSocketMessage):
        """Add message to queue"""
        self.queue.append(message)
        
        if message.requires_ack:
            self.pending_acks[message.message_id] = message
        
        logger.debug(
            f"Message queued",
            extra={
                'message_id': message.message_id,
                'type': message.message_type.value,
                'queue_size': len(self.queue)
            }
        )
    
    def dequeue(self) -> Optional[WebSocketMessage]:
        """Get next message from queue"""
        if self.queue:
            return self.queue.popleft()
        return None
    
    def acknowledge(self, message_id: str):
        """Acknowledge message receipt"""
        if message_id in self.pending_acks:
            message = self.pending_acks[message_id]
            message.acknowledged = True
            del self.pending_acks[message_id]
            logger.debug(f"Message acknowledged: {message_id}")
    
    def get_unacknowledged(self, max_age_seconds: int = 30) -> List[WebSocketMessage]:
        """Get unacknowledged messages older than max_age"""
        now = datetime.utcnow()
        unacked = []
        
        for message in self.pending_acks.values():
            age = (now - message.timestamp).seconds
            if age > max_age_seconds and not message.acknowledged:
                unacked.append(message)
        
        return unacked
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return len(self.queue)
    
    def clear(self):
        """Clear queue"""
        self.queue.clear()
        self.pending_acks.clear()


class HeartbeatMonitor:
    """Monitor connection health with heartbeats"""
    
    def __init__(self, interval: int = 30, timeout: int = 10):
        self.interval = interval  # Heartbeat interval in seconds
        self.timeout = timeout    # Heartbeat timeout in seconds
        self.last_heartbeat: Optional[datetime] = None
        self.last_response: Optional[datetime] = None
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
    
    def start(self, heartbeat_callback: Callable):
        """Start heartbeat monitoring"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_task = asyncio.create_task(
                self._monitor_loop(heartbeat_callback)
            )
            logger.info("Heartbeat monitoring started")
    
    async def _monitor_loop(self, heartbeat_callback: Callable):
        """Heartbeat monitoring loop"""
        while self.is_monitoring:
            try:
                # Send heartbeat
                await heartbeat_callback()
                self.last_heartbeat = datetime.utcnow()
                
                # Wait for interval
                await asyncio.sleep(self.interval)
                
                # Check if we received response
                if self.last_response:
                    age = (datetime.utcnow() - self.last_response).seconds
                    if age > self.timeout:
                        logger.warning(f"Heartbeat timeout: {age}s since last response")
                        # Callback should handle reconnection
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat monitoring error: {e}")
                await asyncio.sleep(5)
    
    def record_response(self):
        """Record heartbeat response"""
        self.last_response = datetime.utcnow()
    
    def stop(self):
        """Stop heartbeat monitoring"""
        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
        logger.info("Heartbeat monitoring stopped")
    
    def is_healthy(self) -> bool:
        """Check if connection is healthy"""
        if not self.last_response:
            return False
        
        age = (datetime.utcnow() - self.last_response).seconds
        return age < self.timeout


class ReconnectionManager:
    """Manage connection reconnection with exponential backoff"""
    
    def __init__(
        self,
        initial_delay: int = 1,
        max_delay: int = 60,
        max_attempts: int = 10
    ):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.max_attempts = max_attempts
        self.current_delay = initial_delay
        self.attempt_count = 0
        self.is_reconnecting = False
    
    async def reconnect(self, connect_callback: Callable) -> bool:
        """
        Attempt to reconnect with exponential backoff
        
        Args:
            connect_callback: Async function to establish connection
            
        Returns:
            True if reconnected successfully
        """
        self.is_reconnecting = True
        
        while self.attempt_count < self.max_attempts:
            self.attempt_count += 1
            
            logger.info(
                f"Reconnection attempt {self.attempt_count}/{self.max_attempts}",
                extra={'delay': self.current_delay}
            )
            
            try:
                # Attempt to connect
                await connect_callback()
                
                # Success - reset counters
                self.reset()
                self.is_reconnecting = False
                logger.info("Reconnection successful")
                return True
                
            except Exception as e:
                logger.error(f"Reconnection attempt failed: {e}")
                
                # Wait before next attempt
                await asyncio.sleep(self.current_delay)
                
                # Exponential backoff
                self.current_delay = min(self.current_delay * 2, self.max_delay)
        
        # Max attempts reached
        self.is_reconnecting = False
        logger.error("Max reconnection attempts reached")
        return False
    
    def reset(self):
        """Reset reconnection state"""
        self.current_delay = self.initial_delay
        self.attempt_count = 0


class WebSocketConnection:
    """Manage a single WebSocket connection"""
    
    def __init__(
        self,
        connection_id: str,
        user_id: str,
        websocket: any  # FastAPI WebSocket
    ):
        self.connection_id = connection_id
        self.user_id = user_id
        self.websocket = websocket
        self.state = ConnectionState.CONNECTED
        self.connected_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.subscriptions: Set[str] = set()
        self.message_queue = MessageQueue()
        self.heartbeat = HeartbeatMonitor()
        self.reconnection = ReconnectionManager()
    
    async def send_message(self, message: WebSocketMessage):
        """Send message to client"""
        try:
            await self.websocket.send_text(message.to_json())
            self.last_activity = datetime.utcnow()
            self.message_queue.enqueue(message)
            
        except Exception as e:
            logger.error(
                f"Error sending message to {self.connection_id}: {e}"
            )
            raise
    
    async def receive_message(self) -> Optional[Dict]:
        """Receive message from client"""
        try:
            data = await self.websocket.receive_text()
            self.last_activity = datetime.utcnow()
            return json.loads(data)
            
        except Exception as e:
            logger.error(
                f"Error receiving message from {self.connection_id}: {e}"
            )
            return None
    
    def subscribe(self, channel: str):
        """Subscribe to a channel"""
        self.subscriptions.add(channel)
        logger.info(
            f"Client subscribed to {channel}",
            extra={'connection_id': self.connection_id, 'user_id': self.user_id}
        )
    
    def unsubscribe(self, channel: str):
        """Unsubscribe from a channel"""
        self.subscriptions.discard(channel)
        logger.info(
            f"Client unsubscribed from {channel}",
            extra={'connection_id': self.connection_id, 'user_id': self.user_id}
        )
    
    def is_subscribed(self, channel: str) -> bool:
        """Check if subscribed to channel"""
        return channel in self.subscriptions
    
    def get_connection_info(self) -> Dict:
        """Get connection information"""
        return {
            'connection_id': self.connection_id,
            'user_id': self.user_id,
            'state': self.state.value,
            'connected_at': self.connected_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'subscriptions': list(self.subscriptions),
            'queue_size': self.message_queue.get_queue_size(),
            'uptime_seconds': (datetime.utcnow() - self.connected_at).seconds
        }


class WebSocketService:
    """
    Main WebSocket service
    Manages connections, subscriptions, and message broadcasting
    """
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.channel_subscribers: Dict[str, Set[str]] = {}  # channel -> connection_ids
        self.cleanup_task: Optional[asyncio.Task] = None
    
    def register_connection(
        self,
        connection_id: str,
        user_id: str,
        websocket: any
    ) -> WebSocketConnection:
        """Register a new WebSocket connection"""
        connection = WebSocketConnection(connection_id, user_id, websocket)
        self.connections[connection_id] = connection
        
        logger.info(
            f"WebSocket connection registered",
            extra={
                'connection_id': connection_id,
                'user_id': user_id,
                'total_connections': len(self.connections)
            }
        )
        
        # Start cleanup task if not running
        if not self.cleanup_task or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        return connection
    
    def unregister_connection(self, connection_id: str):
        """Unregister a WebSocket connection"""
        if connection_id in self.connections:
            connection = self.connections[connection_id]
            
            # Remove from all channels
            for channel in connection.subscriptions:
                if channel in self.channel_subscribers:
                    self.channel_subscribers[channel].discard(connection_id)
            
            # Stop heartbeat monitoring
            connection.heartbeat.stop()
            
            # Remove connection
            del self.connections[connection_id]
            
            logger.info(
                f"WebSocket connection unregistered",
                extra={
                    'connection_id': connection_id,
                    'total_connections': len(self.connections)
                }
            )
    
    def subscribe_to_channel(self, connection_id: str, channel: str):
        """Subscribe connection to a channel"""
        if connection_id in self.connections:
            connection = self.connections[connection_id]
            connection.subscribe(channel)
            
            # Add to channel subscribers
            if channel not in self.channel_subscribers:
                self.channel_subscribers[channel] = set()
            self.channel_subscribers[channel].add(connection_id)
    
    def unsubscribe_from_channel(self, connection_id: str, channel: str):
        """Unsubscribe connection from a channel"""
        if connection_id in self.connections:
            connection = self.connections[connection_id]
            connection.unsubscribe(channel)
            
            # Remove from channel subscribers
            if channel in self.channel_subscribers:
                self.channel_subscribers[channel].discard(connection_id)
    
    async def broadcast_to_channel(self, channel: str, data: Dict):
        """Broadcast message to all subscribers of a channel"""
        if channel not in self.channel_subscribers:
            return
        
        message = WebSocketMessage(
            message_type=MessageType.DATA,
            data={'channel': channel, 'payload': data}
        )
        
        subscribers = self.channel_subscribers[channel].copy()
        tasks = []
        
        for connection_id in subscribers:
            if connection_id in self.connections:
                connection = self.connections[connection_id]
                tasks.append(connection.send_message(message))
        
        # Send to all subscribers concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log failures
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Broadcast error: {result}")
    
    async def send_to_user(self, user_id: str, data: Dict):
        """Send message to all connections of a specific user"""
        message = WebSocketMessage(
            message_type=MessageType.DATA,
            data=data
        )
        
        tasks = []
        for connection in self.connections.values():
            if connection.user_id == user_id:
                tasks.append(connection.send_message(message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _cleanup_loop(self):
        """Periodic cleanup of stale connections"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                now = datetime.utcnow()
                stale_connections = []
                
                for connection_id, connection in self.connections.items():
                    # Check for stale connections (no activity for 5 minutes)
                    age = (now - connection.last_activity).seconds
                    if age > 300:  # 5 minutes
                        stale_connections.append(connection_id)
                
                # Remove stale connections
                for connection_id in stale_connections:
                    logger.warning(f"Removing stale connection: {connection_id}")
                    self.unregister_connection(connection_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
    
    def get_stats(self) -> Dict:
        """Get WebSocket service statistics"""
        total_subscriptions = sum(
            len(conn.subscriptions) for conn in self.connections.values()
        )
        
        return {
            'total_connections': len(self.connections),
            'total_channels': len(self.channel_subscribers),
            'total_subscriptions': total_subscriptions,
            'connections_by_user': self._count_by_user(),
            'subscribers_by_channel': {
                channel: len(subs) 
                for channel, subs in self.channel_subscribers.items()
            }
        }
    
    def _count_by_user(self) -> Dict[str, int]:
        """Count connections by user"""
        user_counts = {}
        for connection in self.connections.values():
            user_id = connection.user_id
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
        return user_counts
    
    async def cleanup(self):
        """Cleanup all resources"""
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for connection_id in list(self.connections.keys()):
            self.unregister_connection(connection_id)


# Global instance
websocket_service = WebSocketService()

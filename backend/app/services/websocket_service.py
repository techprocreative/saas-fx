"""
WebSocket Reliability Service
Implements Phase 2.4 of Production Roadmap
"""
import asyncio
import json
from typing import Dict, Set, Optional, Callable
from datetime import datetime
import logging
from fastapi import WebSocket, WebSocketDisconnect
from collections import deque

logger = logging.getLogger(__name__)


class WebSocketConnection:
    """Represents a single WebSocket connection"""
    
    def __init__(self, websocket: WebSocket, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.connected_at = datetime.utcnow()
        self.last_ping = datetime.utcnow()
        self.last_pong = datetime.utcnow()
        self.missed_pings = 0
        self.message_queue = deque(maxlen=1000)  # Buffer for messages
        self.subscriptions: Set[str] = set()
    
    async def send_json(self, data: Dict):
        """Send JSON message to client"""
        try:
            await self.websocket.send_json(data)
            return True
        except Exception as e:
            logger.error(f"Error sending message to {self.client_id}: {e}")
            return False
    
    async def send_text(self, message: str):
        """Send text message to client"""
        try:
            await self.websocket.send_text(message)
            return True
        except Exception as e:
            logger.error(f"Error sending text to {self.client_id}: {e}")
            return False
    
    async def receive_json(self) -> Optional[Dict]:
        """Receive JSON message from client"""
        try:
            return await self.websocket.receive_json()
        except Exception as e:
            logger.error(f"Error receiving from {self.client_id}: {e}")
            return None
    
    def queue_message(self, message: Dict):
        """Queue message for delivery"""
        self.message_queue.append({
            'timestamp': datetime.utcnow().isoformat(),
            'data': message
        })
    
    async def flush_queue(self):
        """Send all queued messages"""
        while self.message_queue:
            message = self.message_queue.popleft()
            success = await self.send_json(message['data'])
            if not success:
                # Put message back if sending failed
                self.message_queue.appendleft(message)
                break


class ConnectionManager:
    """Manage WebSocket connections with reliability features"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocketConnection] = {}
        self.topic_subscribers: Dict[str, Set[str]] = {}  # topic -> set of client_ids
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_timeout = 90  # seconds
        self.max_missed_pings = 3
    
    async def connect(self, websocket: WebSocket, client_id: str) -> WebSocketConnection:
        """Accept new WebSocket connection"""
        await websocket.accept()
        
        connection = WebSocketConnection(websocket, client_id)
        self.active_connections[client_id] = connection
        
        logger.info(f"Client {client_id} connected. Total connections: {len(self.active_connections)}")
        
        # Start heartbeat for this connection
        asyncio.create_task(self._heartbeat_monitor(client_id))
        
        return connection
    
    def disconnect(self, client_id: str):
        """Remove connection"""
        if client_id in self.active_connections:
            connection = self.active_connections[client_id]
            
            # Remove from all topic subscriptions
            for topic in connection.subscriptions:
                if topic in self.topic_subscribers:
                    self.topic_subscribers[topic].discard(client_id)
            
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, client_id: str, message: Dict):
        """Send message to specific client"""
        connection = self.active_connections.get(client_id)
        if connection:
            return await connection.send_json(message)
        return False
    
    async def broadcast(self, message: Dict, exclude: Optional[Set[str]] = None):
        """Broadcast message to all connected clients"""
        exclude = exclude or set()
        
        for client_id, connection in self.active_connections.items():
            if client_id not in exclude:
                await connection.send_json(message)
    
    async def broadcast_to_topic(self, topic: str, message: Dict):
        """Broadcast message to all subscribers of a topic"""
        if topic not in self.topic_subscribers:
            return
        
        subscribers = self.topic_subscribers[topic].copy()
        
        for client_id in subscribers:
            connection = self.active_connections.get(client_id)
            if connection:
                # Queue message for reliability
                connection.queue_message(message)
                await connection.send_json(message)
    
    def subscribe(self, client_id: str, topic: str):
        """Subscribe client to a topic"""
        connection = self.active_connections.get(client_id)
        if not connection:
            return False
        
        if topic not in self.topic_subscribers:
            self.topic_subscribers[topic] = set()
        
        self.topic_subscribers[topic].add(client_id)
        connection.subscriptions.add(topic)
        
        logger.info(f"Client {client_id} subscribed to {topic}")
        return True
    
    def unsubscribe(self, client_id: str, topic: str):
        """Unsubscribe client from a topic"""
        connection = self.active_connections.get(client_id)
        if not connection:
            return False
        
        if topic in self.topic_subscribers:
            self.topic_subscribers[topic].discard(client_id)
        
        connection.subscriptions.discard(topic)
        
        logger.info(f"Client {client_id} unsubscribed from {topic}")
        return True
    
    async def _heartbeat_monitor(self, client_id: str):
        """Monitor connection health with heartbeat"""
        while client_id in self.active_connections:
            connection = self.active_connections[client_id]
            
            try:
                # Send ping
                await connection.send_json({
                    'type': 'ping',
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                connection.last_ping = datetime.utcnow()
                
                # Check for pong timeout
                time_since_pong = (datetime.utcnow() - connection.last_pong).seconds
                
                if time_since_pong > self.heartbeat_timeout:
                    connection.missed_pings += 1
                    logger.warning(f"Client {client_id} missed ping {connection.missed_pings}/{self.max_missed_pings}")
                    
                    if connection.missed_pings >= self.max_missed_pings:
                        logger.error(f"Client {client_id} exceeded max missed pings. Disconnecting.")
                        self.disconnect(client_id)
                        break
                else:
                    connection.missed_pings = 0
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Heartbeat error for {client_id}: {e}")
                self.disconnect(client_id)
                break
    
    def get_connection_stats(self) -> Dict:
        """Get connection statistics"""
        return {
            'total_connections': len(self.active_connections),
            'topics': len(self.topic_subscribers),
            'connections': [
                {
                    'client_id': conn.client_id,
                    'connected_at': conn.connected_at.isoformat(),
                    'subscriptions': list(conn.subscriptions),
                    'queued_messages': len(conn.message_queue),
                    'missed_pings': conn.missed_pings
                }
                for conn in self.active_connections.values()
            ]
        }


class WebSocketService:
    """
    Main WebSocket service with reliability features
    """
    
    def __init__(self):
        self.manager = ConnectionManager()
        self.message_handlers: Dict[str, Callable] = {}
    
    def register_handler(self, message_type: str, handler: Callable):
        """Register message handler"""
        self.message_handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")
    
    async def handle_connection(self, websocket: WebSocket, client_id: str):
        """
        Handle WebSocket connection lifecycle
        
        Args:
            websocket: FastAPI WebSocket instance
            client_id: Unique client identifier
        """
        connection = await self.manager.connect(websocket, client_id)
        
        try:
            # Send welcome message
            await connection.send_json({
                'type': 'connected',
                'client_id': client_id,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Main message loop
            while True:
                try:
                    # Receive message with timeout
                    data = await asyncio.wait_for(
                        connection.receive_json(),
                        timeout=60.0
                    )
                    
                    if data:
                        await self._process_message(connection, data)
                
                except asyncio.TimeoutError:
                    # No message received, continue
                    continue
                    
                except WebSocketDisconnect:
                    logger.info(f"Client {client_id} disconnected normally")
                    break
                    
                except Exception as e:
                    logger.error(f"Error in message loop for {client_id}: {e}")
                    break
        
        finally:
            self.manager.disconnect(client_id)
    
    async def _process_message(self, connection: WebSocketConnection, data: Dict):
        """Process incoming message"""
        message_type = data.get('type')
        
        if not message_type:
            await connection.send_json({
                'type': 'error',
                'message': 'Message type required'
            })
            return
        
        # Handle pong
        if message_type == 'pong':
            connection.last_pong = datetime.utcnow()
            connection.missed_pings = 0
            return
        
        # Handle subscribe
        if message_type == 'subscribe':
            topic = data.get('topic')
            if topic:
                self.manager.subscribe(connection.client_id, topic)
                await connection.send_json({
                    'type': 'subscribed',
                    'topic': topic
                })
            return
        
        # Handle unsubscribe
        if message_type == 'unsubscribe':
            topic = data.get('topic')
            if topic:
                self.manager.unsubscribe(connection.client_id, topic)
                await connection.send_json({
                    'type': 'unsubscribed',
                    'topic': topic
                })
            return
        
        # Handle custom message types
        handler = self.message_handlers.get(message_type)
        if handler:
            try:
                await handler(connection, data)
            except Exception as e:
                logger.error(f"Error in handler for {message_type}: {e}")
                await connection.send_json({
                    'type': 'error',
                    'message': f'Handler error: {str(e)}'
                })
        else:
            await connection.send_json({
                'type': 'error',
                'message': f'Unknown message type: {message_type}'
            })
    
    async def broadcast_price_update(self, symbol: str, price_data: Dict):
        """Broadcast price update to subscribers"""
        topic = f"price:{symbol}"
        message = {
            'type': 'price_update',
            'symbol': symbol,
            'data': price_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        await self.manager.broadcast_to_topic(topic, message)
    
    async def broadcast_signal_update(self, symbol: str, signal_data: Dict):
        """Broadcast trading signal to subscribers"""
        topic = f"signal:{symbol}"
        message = {
            'type': 'signal_update',
            'symbol': symbol,
            'data': signal_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        await self.manager.broadcast_to_topic(topic, message)
    
    async def broadcast_order_update(self, user_id: str, order_data: Dict):
        """Broadcast order update to specific user"""
        message = {
            'type': 'order_update',
            'data': order_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        await self.manager.send_personal_message(user_id, message)
    
    def get_stats(self) -> Dict:
        """Get service statistics"""
        return self.manager.get_connection_stats()


# Global instance
websocket_service = WebSocketService()

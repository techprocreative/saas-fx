"""
WebSocket API Endpoints for Real-Time Data
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional
import asyncio
import json
import logging

from app.core.auth import get_current_user_ws
from app.services.websocket_service import websocket_service, MessageType
from app.services.market_data_service import market_data_service
from app.services.signal_service import signal_service
from app.services.order_service import order_service

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/{connection_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    connection_id: str,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time data streaming
    
    - **connection_id**: Unique connection identifier
    - **token**: JWT authentication token (query parameter)
    
    ## Message Types:
    
    **Client → Server:**
    - `subscribe`: Subscribe to a channel
      ```json
      {
        "type": "subscribe",
        "data": {"channel": "prices", "symbols": ["EUR/USD", "GBP/USD"]}
      }
      ```
    
    - `unsubscribe`: Unsubscribe from a channel
      ```json
      {
        "type": "unsubscribe",
        "data": {"channel": "prices"}
      }
      ```
    
    - `heartbeat`: Keep-alive ping
      ```json
      {
        "type": "heartbeat",
        "data": {}
      }
      ```
    
    **Server → Client:**
    - `data`: Data update
      ```json
      {
        "type": "data",
        "data": {
          "channel": "prices",
          "payload": {"symbol": "EUR/USD", "price": 1.0851}
        }
      }
      ```
    
    - `ack`: Acknowledgment
    - `error`: Error message
    
    ## Available Channels:
    - `prices` - Real-time price updates
    - `signals` - Trading signal updates
    - `orders` - Order status updates
    - `portfolio` - Portfolio updates
    """
    # Accept WebSocket connection
    await websocket.accept()
    
    try:
        # Authenticate user (simplified - in production use proper JWT validation)
        # For now, we'll use a mock user_id from connection_id
        user_id = connection_id.split("-")[0] if "-" in connection_id else connection_id
        
        # Register connection
        connection = websocket_service.register_connection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=websocket
        )
        
        logger.info(f"WebSocket connection established: {connection_id}")
        
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "data": {
                "connection_id": connection_id,
                "message": "Connected successfully",
                "available_channels": ["prices", "signals", "orders", "portfolio"]
            }
        })
        
        # Background tasks for streaming data
        tasks = []
        
        # Main message loop
        while True:
            try:
                # Receive message from client
                message = await websocket.receive_json()
                message_type = message.get("type")
                data = message.get("data", {})
                
                if message_type == "subscribe":
                    # Subscribe to channel
                    channel = data.get("channel")
                    if channel:
                        websocket_service.subscribe_to_channel(connection_id, channel)
                        
                        # Start streaming task for this channel
                        if channel == "prices":
                            symbols = data.get("symbols", ["EUR/USD"])
                            task = asyncio.create_task(
                                stream_prices(connection_id, symbols)
                            )
                            tasks.append(task)
                        
                        elif channel == "signals":
                            symbols = data.get("symbols", ["EUR/USD"])
                            task = asyncio.create_task(
                                stream_signals(connection_id, symbols)
                            )
                            tasks.append(task)
                        
                        elif channel == "orders":
                            task = asyncio.create_task(
                                stream_orders(connection_id, user_id)
                            )
                            tasks.append(task)
                        
                        # Send acknowledgment
                        await websocket.send_json({
                            "type": "ack",
                            "data": {
                                "channel": channel,
                                "subscribed": True
                            }
                        })
                
                elif message_type == "unsubscribe":
                    # Unsubscribe from channel
                    channel = data.get("channel")
                    if channel:
                        websocket_service.unsubscribe_from_channel(connection_id, channel)
                        
                        # Send acknowledgment
                        await websocket.send_json({
                            "type": "ack",
                            "data": {
                                "channel": channel,
                                "subscribed": False
                            }
                        })
                
                elif message_type == "heartbeat":
                    # Respond to heartbeat
                    connection.heartbeat.record_response()
                    await websocket.send_json({
                        "type": "heartbeat",
                        "data": {"status": "alive"}
                    })
                
                else:
                    # Unknown message type
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": f"Unknown message type: {message_type}"}
                    })
            
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {connection_id}")
                break
            
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid JSON format"}
                })
            
            except Exception as e:
                logger.error(f"Error in WebSocket loop: {e}")
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": str(e)}
                })
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    
    finally:
        # Cancel all background tasks
        for task in tasks:
            task.cancel()
        
        # Unregister connection
        websocket_service.unregister_connection(connection_id)
        logger.info(f"WebSocket connection closed: {connection_id}")


async def stream_prices(connection_id: str, symbols: list):
    """Stream real-time price updates"""
    try:
        while True:
            if connection_id not in websocket_service.connections:
                break
            
            connection = websocket_service.connections[connection_id]
            
            if not connection.is_subscribed("prices"):
                break
            
            # Get current prices for symbols
            for symbol in symbols:
                try:
                    price_data = await market_data_service.get_current_price(symbol, use_cache=False)
                    
                    await websocket_service.broadcast_to_channel("prices", {
                        "symbol": symbol,
                        "price": price_data['price'],
                        "bid": price_data['bid'],
                        "ask": price_data['ask'],
                        "timestamp": price_data['timestamp'].isoformat()
                    })
                
                except Exception as e:
                    logger.error(f"Error streaming price for {symbol}: {e}")
            
            # Update every second
            await asyncio.sleep(1)
    
    except asyncio.CancelledError:
        pass


async def stream_signals(connection_id: str, symbols: list):
    """Stream trading signal updates"""
    try:
        while True:
            if connection_id not in websocket_service.connections:
                break
            
            connection = websocket_service.connections[connection_id]
            
            if not connection.is_subscribed("signals"):
                break
            
            # Get signals for symbols
            for symbol in symbols:
                try:
                    signal = await signal_service.get_signal(symbol)
                    
                    if signal:
                        await websocket_service.broadcast_to_channel("signals", {
                            "symbol": symbol,
                            "signal_type": signal.signal_type.value,
                            "strength": signal.strength.value,
                            "confidence": signal.confidence,
                            "entry_price": signal.entry_price,
                            "take_profit": signal.take_profit,
                            "stop_loss": signal.stop_loss,
                            "timestamp": signal.timestamp.isoformat()
                        })
                
                except Exception as e:
                    logger.error(f"Error streaming signal for {symbol}: {e}")
            
            # Update every 5 seconds
            await asyncio.sleep(5)
    
    except asyncio.CancelledError:
        pass


async def stream_orders(connection_id: str, user_id: str):
    """Stream order status updates"""
    try:
        last_order_count = 0
        
        while True:
            if connection_id not in websocket_service.connections:
                break
            
            connection = websocket_service.connections[connection_id]
            
            if not connection.is_subscribed("orders"):
                break
            
            # Get user's active orders
            try:
                orders = order_service.get_user_orders(user_id, active_only=True)
                
                # Send update if orders changed
                if len(orders) != last_order_count:
                    await websocket_service.send_to_user(user_id, {
                        "channel": "orders",
                        "active_orders": len(orders),
                        "orders": orders[:5]  # Send only first 5 for performance
                    })
                    
                    last_order_count = len(orders)
            
            except Exception as e:
                logger.error(f"Error streaming orders for user {user_id}: {e}")
            
            # Update every 2 seconds
            await asyncio.sleep(2)
    
    except asyncio.CancelledError:
        pass


@router.get("/ws/stats")
async def get_websocket_stats():
    """
    Get WebSocket service statistics
    
    Returns current connection count, active channels, etc.
    """
    return websocket_service.get_stats()

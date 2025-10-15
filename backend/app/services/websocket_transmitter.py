import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import TradingAccount, Trade, User

logger = logging.getLogger(__name__)

class SignalTransmitter:
    """WebSocket service for transmitting trading signals to users' MT5 terminals"""
    
    def __init__(self):
        self.connected_clients: Dict[str, WebSocket] = {}  # user_id: websocket
        self.connected_accounts: Dict[str, str] = {}  # connection_id: user_id
        self.signal_queue = asyncio.Queue()
        self._heartbeat_task: Optional[asyncio.Task] = None
        
    async def handle_client_connection(self, websocket: WebSocket, user_id: str):
        """Handle WebSocket connection from user's PyTrader client"""
        await websocket.accept()
        self.connected_clients[user_id] = websocket
        connection_id = f"{user_id}_{datetime.now().timestamp()}"
        self.connected_accounts[connection_id] = user_id
        
        logger.info(f"User {user_id} connected via WebSocket")
        
        # Update account connection status
        try:
            # This would need database session injection
            from app.core.database import get_db
            db = next(get_db())
            accounts = db.query(TradingAccount).filter(
                TradingAccount.user_id == user_id
            ).all()
            
            for account in accounts:
                account.connection_status = "online"
                account.websocket_connection_id = connection_id
                account.last_ping = datetime.utcnow()
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error updating account status: {e}")
        
        try:
            # Send initial connection confirmation
            await websocket.send_json({
                'type': 'connection_established',
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat(),
                'server_time': datetime.utcnow().isoformat()
            })
            
            # Start heartbeat loop
            if not self._heartbeat_task or self._heartbeat_task.done():
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # Listen for messages from client
            while True:
                message = await websocket.receive_json()
                await self._process_client_message(user_id, message)
                
        except WebSocketDisconnect:
            logger.info(f"User {user_id} disconnected")
        except Exception as e:
            logger.error(f"WebSocket error for user {user_id}: {e}")
        finally:
            await self._cleanup_disconnection(user_id, connection_id)
    
    async def _process_client_message(self, user_id: str, message: dict):
        """Process incoming messages from client"""
        message_type = message.get('type')
        
        if message_type == 'ping':
            await self._handle_ping(user_id, message)
        elif message_type == 'trade_result':
            await self._handle_trade_result(user_id, message)
        elif message_type == 'account_status':
            await self._handle_account_status(user_id, message)
        elif message_type == 'heartbeat':
            await self._handle_heartbeat(user_id)
        else:
            logger.warning(f"Unknown message type: {message_type} from user {user_id}")
    
    async def _handle_ping(self, user_id: str, message: dict):
        """Handle ping message from client"""
        account_data = message.get('account_data', {})
        
        # Update account status
        try:
            from app.core.database import get_db
            db = next(get_db())
            accounts = db.query(TradingAccount).filter(
                TradingAccount.user_id == user_id
            ).all()
            
            for account in accounts:
                account.last_ping = datetime.utcnow()
                if 'balance' in account_data:
                    account.balance = account_data['balance']
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error updating ping status: {e}")
        
        # Send pong response
        await self.send_to_client(user_id, {
            'type': 'pong',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def _handle_trade_result(self, user_id: str, message: dict):
        """Handle trade execution result from client"""
        trade_data = message.get('trade_data', {})
        signal_id = message.get('signal_id')
        
        logger.info(f"Received trade result for signal {signal_id}: {trade_data}")
        
        # Update trade in database
        try:
            from app.core.database import get_db
            from app.models import Trade, CommissionStatus, TradeStatus
            
            db = next(get_db())
            
            # Find the trade by signal_id (assuming signal_id correlates with trade.id)
            trade = db.query(Trade).filter(
                Trade.id == signal_id,
                Trade.account_id.in_(
                    db.query(TradingAccount.id).filter(
                        TradingAccount.user_id == user_id
                    )
                )
            ).first()
            
            if trade:
                # Update trade information
                trade.status = TradeStatus.CLOSED if trade_data.get('status') == 'executed' else TradeStatus.OPEN
                trade.mt5_order_id = trade_data.get('order_id')
                trade.mt5_position_id = trade_data.get('position_id')
                trade.close_price = trade_data.get('execution_price')
                trade.profit_loss = trade_data.get('profit', 0.0)
                trade.closed_at = datetime.utcnow()
                
                # Calculate commission if profitable
                if trade.profit_loss > 0:
                    from app.services.commission_service import CommissionCalculator
                    calculator = CommissionCalculator()
                    commission_data = calculator.calculate_commission({
                        'id': str(trade.id),
                        'volume': float(trade.volume),
                        'profit_loss': float(trade.profit_loss)
                    })
                    
                    commission = Commission(
                        trade_id=trade.id,
                        user_id=user_id,
                        amount=commission_data['total'],
                        volume_commission=commission_data['volume_commission'],
                        profit_commission=commission_data['profit_commission'],
                        status='pending'
                    )
                    db.add(commission)
                
                db.commit()
                logger.info(f"Updated trade {trade.id} with execution result")
            else:
                logger.warning(f"Trade not found for signal_id: {signal_id}")
                
        except Exception as e:
            logger.error(f"Error processing trade result: {e}")
    
    async def _handle_account_status(self, user_id: str, message: dict):
        """Handle account status update"""
        account_data = message.get('account_data', {})
        logger.info(f"Account status update from user {user_id}: {account_data}")
        
        # Update account information
        try:
            from app.core.database import get_db
            db = next(get_db())
            
            for acc_data in account_data:
                account = db.query(TradingAccount).filter(
                    TradingAccount.user_id == user_id,
                    TradingAccount.mt5_login == acc_data.get('login')
                ).first()
                
                if account:
                    account.balance = acc_data.get('balance', account.balance)
                    account.last_ping = datetime.utcnow()
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error updating account status: {e}")
    
    async def _handle_heartbeat(self, user_id: str):
        """Handle heartbeat message"""
        # Update last ping timestamp
        try:
            from app.core.database import get_db
            db = next(get_db())
            accounts = db.query(TradingAccount).filter(
                TradingAccount.user_id == user_id
            ).all()
            
            for account in accounts:
                account.last_ping = datetime.utcnow()
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error updating heartbeat: {e}")
    
    async def send_signal_to_user(self, user_id: str, signal: dict) -> bool:
        """Send trading signal to specific user's MT5 via WebSocket"""
        if user_id not in self.connected_clients:
            logger.warning(f"User {user_id} not connected via WebSocket")
            # Queue signal for when user reconnects
            await self.queue_signal_for_user(user_id, signal)
            return False
        
        websocket = self.connected_clients[user_id]
        try:
            await websocket.send_json({
                'type': 'trading_signal',
                'signal': signal,
                'timestamp': datetime.utcnow().isoformat()
            })
            logger.info(f"Signal sent to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send signal to user {user_id}: {e}")
            await self.handle_failed_transmission(user_id, signal)
            return False
    
    async def send_to_client(self, user_id: str, data: dict) -> bool:
        """Send general message to client"""
        if user_id not in self.connected_clients:
            return False
        
        try:
            websocket = self.connected_clients[user_id]
            await websocket.send_json(data)
            return True
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")
            return False
    
    async def queue_signal_for_user(self, user_id: str, signal: dict):
        """Queue signal for when user reconnects"""
        await self.signal_queue.put({
            'user_id': user_id,
            'signal': signal,
            'timestamp': datetime.utcnow().isoformat()
        })
        logger.info(f"Signal queued for user {user_id}")
    
    async def handle_failed_transmission(self, user_id: str, signal: dict):
        """Handle failed signal transmission"""
        logger.error(f"Signal transmission failed for user {user_id}")
        # Queue the signal for retry
        await self.queue_signal_for_user(user_id, signal)
    
    async def _cleanup_disconnection(self, user_id: str, connection_id: str):
        """Cleanup when user disconnects"""
        if user_id in self.connected_clients:
            del self.connected_clients[user_id]
        
        if connection_id in self.connected_accounts:
            del self.connected_accounts[connection_id]
        
        # Update account connection status
        try:
            from app.core.database import get_db
            db = next(get_db())
            accounts = db.query(TradingAccount).filter(
                TradingAccount.user_id == user_id
            ).all()
            
            for account in accounts:
                account.connection_status = "offline"
                account.websocket_connection_id = None
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error cleaning up disconnection: {e}")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat to connected clients"""
        while True:
            try:
                await asyncio.sleep(settings.CLIENT_HEARTBEAT_INTERVAL)
                
                disconnected_users = []
                for user_id, websocket in self.connected_clients.items():
                    try:
                        await websocket.send_json({
                            'type': 'heartbeat',
                            'timestamp': datetime.utcnow().isoformat()
                        })
                    except:
                        disconnected_users.append(user_id)
                
                # Remove disconnected users
                for user_id in disconnected_users:
                    if user_id in self.connected_clients:
                        del self.connected_clients[user_id]
                    logger.warning(f"User {user_id} failed heartbeat, removed from connected list")
                
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
    
    def get_connected_users(self) -> Set[str]:
        """Get list of currently connected user IDs"""
        return set(self.connected_clients.keys())
    
    def is_user_connected(self, user_id: str) -> bool:
        """Check if user is currently connected"""
        return user_id in self.connected_clients

# Global instance
signal_transmitter = SignalTransmitter()

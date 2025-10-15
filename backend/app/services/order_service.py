"""
Order Management Service
Implements Phase 2.3 of Production Roadmap
"""
import asyncio
import uuid
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from pybreaker import CircuitBreaker

from app.services.signal_service import TradingSignal

logger = logging.getLogger(__name__)


class OrderType(str, Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, Enum):
    """Order side"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """Order status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    FAILED = "failed"


class Order:
    """Trading order data structure"""
    
    def __init__(
        self,
        user_id: str,
        symbol: str,
        order_type: OrderType,
        side: OrderSide,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
        signal_id: Optional[str] = None
    ):
        self.order_id = str(uuid.uuid4())
        self.user_id = user_id
        self.symbol = symbol
        self.order_type = order_type
        self.side = side
        self.quantity = quantity
        self.price = price
        self.stop_price = stop_price
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.signal_id = signal_id
        
        self.status = OrderStatus.PENDING
        self.filled_quantity = 0.0
        self.average_fill_price = 0.0
        self.commission = 0.0
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.executed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.retry_count = 0
    
    def to_dict(self) -> Dict:
        """Convert order to dictionary"""
        return {
            'order_id': self.order_id,
            'user_id': self.user_id,
            'symbol': self.symbol,
            'order_type': self.order_type.value,
            'side': self.side.value,
            'quantity': self.quantity,
            'price': self.price,
            'stop_price': self.stop_price,
            'take_profit': self.take_profit,
            'stop_loss': self.stop_loss,
            'signal_id': self.signal_id,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'average_fill_price': self.average_fill_price,
            'commission': self.commission,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'error_message': self.error_message,
            'retry_count': self.retry_count
        }
    
    def update_status(self, status: OrderStatus, error_message: Optional[str] = None):
        """Update order status"""
        self.status = status
        self.updated_at = datetime.utcnow()
        if error_message:
            self.error_message = error_message
        if status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]:
            if not self.executed_at:
                self.executed_at = datetime.utcnow()


class OrderExecutor:
    """Execute orders against trading platform"""
    
    def __init__(self):
        # Circuit breaker for external API calls
        self.circuit_breaker = CircuitBreaker(
            fail_max=5,
            timeout_duration=60,
            name="order_executor"
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def execute_order(self, order: Order) -> bool:
        """
        Execute order on trading platform
        
        Args:
            order: Order to execute
            
        Returns:
            True if successful
        """
        try:
            order.retry_count += 1
            
            # Use circuit breaker
            with self.circuit_breaker:
                # Simulate order execution (replace with real API call)
                await asyncio.sleep(0.1)  # Simulate network delay
                
                # Mock execution logic
                import random
                success_rate = 0.95  # 95% success rate
                
                if random.random() < success_rate:
                    # Order successful
                    order.status = OrderStatus.FILLED
                    order.filled_quantity = order.quantity
                    order.average_fill_price = order.price or self._get_market_price(order.symbol)
                    order.commission = order.filled_quantity * order.average_fill_price * 0.001  # 0.1% commission
                    order.executed_at = datetime.utcnow()
                    
                    logger.info(
                        f"Order executed successfully",
                        extra={
                            'order_id': order.order_id,
                            'symbol': order.symbol,
                            'side': order.side.value,
                            'quantity': order.quantity,
                            'price': order.average_fill_price
                        }
                    )
                    return True
                else:
                    # Order failed
                    error_msg = "Execution failed: Insufficient liquidity"
                    order.update_status(OrderStatus.FAILED, error_msg)
                    logger.error(
                        f"Order execution failed: {error_msg}",
                        extra={'order_id': order.order_id}
                    )
                    return False
                    
        except Exception as e:
            error_msg = f"Order execution error: {str(e)}"
            order.update_status(OrderStatus.FAILED, error_msg)
            logger.error(error_msg, extra={'order_id': order.order_id})
            raise
    
    def _get_market_price(self, symbol: str) -> float:
        """Get current market price (mock)"""
        # In production, get from market data service
        import random
        base_price = 1.0500 if 'EUR' in symbol else 1800.0
        return base_price + random.uniform(-0.001, 0.001)
    
    async def cancel_order(self, order: Order) -> bool:
        """Cancel an order"""
        try:
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                logger.warning(f"Cannot cancel order in status {order.status.value}")
                return False
            
            # Simulate cancellation (replace with real API call)
            await asyncio.sleep(0.05)
            
            order.update_status(OrderStatus.CANCELLED)
            logger.info(f"Order cancelled", extra={'order_id': order.order_id})
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False


class OrderQueue:
    """Manage order queue with priority"""
    
    def __init__(self):
        self.queue: List[Order] = []
        self.processing = False
    
    def add_order(self, order: Order, priority: bool = False):
        """Add order to queue"""
        if priority:
            self.queue.insert(0, order)
        else:
            self.queue.append(order)
        
        logger.info(
            f"Order added to queue",
            extra={'order_id': order.order_id, 'queue_size': len(self.queue)}
        )
    
    def get_next_order(self) -> Optional[Order]:
        """Get next order from queue"""
        if self.queue:
            return self.queue.pop(0)
        return None
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return len(self.queue)
    
    def clear_queue(self):
        """Clear all orders from queue"""
        self.queue.clear()


class OrderService:
    """
    Main order management service
    Handles order submission, execution, and tracking
    """
    
    def __init__(self):
        self.executor = OrderExecutor()
        self.queue = OrderQueue()
        self.active_orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        self.processing_task: Optional[asyncio.Task] = None
    
    async def create_order(
        self,
        user_id: str,
        symbol: str,
        order_type: OrderType,
        side: OrderSide,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
        signal: Optional[TradingSignal] = None
    ) -> Order:
        """
        Create a new order
        
        Args:
            user_id: User ID
            symbol: Trading symbol
            order_type: Order type
            side: Buy or sell
            quantity: Order quantity
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            take_profit: Take profit price
            stop_loss: Stop loss price
            signal: Associated trading signal
            
        Returns:
            Created order
        """
        # Validate order
        self._validate_order(order_type, side, quantity, price, stop_price)
        
        # Create order
        order = Order(
            user_id=user_id,
            symbol=symbol,
            order_type=order_type,
            side=side,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            take_profit=take_profit,
            stop_loss=stop_loss,
            signal_id=signal.timestamp.isoformat() if signal else None
        )
        
        # Add to active orders
        self.active_orders[order.order_id] = order
        
        # Add to queue
        priority = order_type == OrderType.MARKET  # Market orders have priority
        self.queue.add_order(order, priority=priority)
        
        # Start processing if not already running
        if not self.processing_task or self.processing_task.done():
            self.processing_task = asyncio.create_task(self._process_queue())
        
        logger.info(
            f"Order created",
            extra={
                'order_id': order.order_id,
                'user_id': user_id,
                'symbol': symbol,
                'side': side.value,
                'quantity': quantity
            }
        )
        
        return order
    
    def _validate_order(
        self,
        order_type: OrderType,
        side: OrderSide,
        quantity: float,
        price: Optional[float],
        stop_price: Optional[float]
    ):
        """Validate order parameters"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if order_type == OrderType.LIMIT and not price:
            raise ValueError("Limit orders require a price")
        
        if order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and not stop_price:
            raise ValueError("Stop orders require a stop price")
        
        if order_type == OrderType.STOP_LIMIT and not price:
            raise ValueError("Stop-limit orders require both stop price and limit price")
    
    async def _process_queue(self):
        """Process orders from queue"""
        self.queue.processing = True
        
        try:
            while True:
                order = self.queue.get_next_order()
                
                if not order:
                    # Queue is empty, wait a bit
                    await asyncio.sleep(0.5)
                    
                    # Check if queue is still empty
                    if self.queue.get_queue_size() == 0:
                        break
                    continue
                
                # Update order status
                order.update_status(OrderStatus.SUBMITTED)
                
                # Execute order
                try:
                    success = await self.executor.execute_order(order)
                    
                    if success:
                        # Move to history
                        self.order_history.append(order)
                        
                        # Remove from active orders
                        if order.order_id in self.active_orders:
                            del self.active_orders[order.order_id]
                    else:
                        # Keep in active orders for retry or manual intervention
                        logger.warning(
                            f"Order execution failed, keeping in active orders",
                            extra={'order_id': order.order_id}
                        )
                        
                except Exception as e:
                    logger.error(
                        f"Error processing order: {e}",
                        extra={'order_id': order.order_id}
                    )
                    order.update_status(OrderStatus.FAILED, str(e))
                
                # Small delay between orders
                await asyncio.sleep(0.1)
                
        finally:
            self.queue.processing = False
            logger.info("Order queue processing completed")
    
    async def cancel_order(self, order_id: str, user_id: str) -> bool:
        """
        Cancel an order
        
        Args:
            order_id: Order ID
            user_id: User ID (for authorization)
            
        Returns:
            True if cancelled successfully
        """
        order = self.active_orders.get(order_id)
        
        if not order:
            logger.warning(f"Order not found: {order_id}")
            return False
        
        if order.user_id != user_id:
            logger.warning(f"Unauthorized cancel attempt for order {order_id}")
            return False
        
        return await self.executor.cancel_order(order)
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        # Check active orders first
        if order_id in self.active_orders:
            return self.active_orders[order_id]
        
        # Check history
        for order in self.order_history:
            if order.order_id == order_id:
                return order
        
        return None
    
    def get_user_orders(self, user_id: str, active_only: bool = False) -> List[Dict]:
        """Get all orders for a user"""
        orders = []
        
        # Active orders
        for order in self.active_orders.values():
            if order.user_id == user_id:
                orders.append(order.to_dict())
        
        # Historical orders
        if not active_only:
            for order in self.order_history:
                if order.user_id == user_id:
                    orders.append(order.to_dict())
        
        # Sort by created_at descending
        orders.sort(key=lambda x: x['created_at'], reverse=True)
        
        return orders
    
    def get_order_stats(self) -> Dict:
        """Get order statistics"""
        total_orders = len(self.active_orders) + len(self.order_history)
        
        filled_orders = sum(
            1 for o in self.order_history 
            if o.status == OrderStatus.FILLED
        )
        
        failed_orders = sum(
            1 for o in self.order_history 
            if o.status == OrderStatus.FAILED
        )
        
        return {
            'total_orders': total_orders,
            'active_orders': len(self.active_orders),
            'historical_orders': len(self.order_history),
            'filled_orders': filled_orders,
            'failed_orders': failed_orders,
            'queue_size': self.queue.get_queue_size(),
            'success_rate': (filled_orders / total_orders * 100) if total_orders > 0 else 0
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.processing_task and not self.processing_task.done():
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass


# Global instance
order_service = OrderService()

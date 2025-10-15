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


class Order:
    """Order data class"""
    
    def __init__(
        self,
        user_id: str,
        symbol: str,
        order_type: OrderType,
        side: OrderSide,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        order_id: Optional[str] = None
    ):
        self.order_id = order_id or str(uuid.uuid4())
        self.user_id = user_id
        self.symbol = symbol
        self.order_type = order_type
        self.side = side
        self.quantity = quantity
        self.price = price
        self.stop_price = stop_price
        self.status = OrderStatus.PENDING
        self.filled_quantity = 0.0
        self.average_price = 0.0
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.executed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.retry_count = 0
        self.external_order_id: Optional[str] = None
    
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
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'average_price': self.average_price,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'external_order_id': self.external_order_id
        }


class OrderValidator:
    """Validate orders before submission"""
    
    @staticmethod
    def validate_order(order: Order) -> tuple[bool, Optional[str]]:
        """
        Validate order parameters
        
        Returns:
            (is_valid, error_message)
        """
        # Check quantity
        if order.quantity <= 0:
            return False, "Quantity must be greater than 0"
        
        # Check limit order has price
        if order.order_type == OrderType.LIMIT and order.price is None:
            return False, "Limit orders must have a price"
        
        # Check stop order has stop_price
        if order.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
            if order.stop_price is None:
                return False, "Stop orders must have a stop price"
        
        # Check stop_limit has both prices
        if order.order_type == OrderType.STOP_LIMIT:
            if order.price is None:
                return False, "Stop limit orders must have both price and stop_price"
        
        # Check symbol format
        if not order.symbol or len(order.symbol) < 6:
            return False, "Invalid symbol format"
        
        return True, None
    
    @staticmethod
    def calculate_order_value(order: Order, current_price: float) -> float:
        """Calculate estimated order value"""
        price = order.price if order.price else current_price
        return order.quantity * price


class OrderExecutor:
    """Execute orders with retry logic"""
    
    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 2  # seconds
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def execute_order(self, order: Order) -> bool:
        """
        Execute order with retry logic
        
        Args:
            order: Order to execute
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Executing order {order.order_id}")
            
            # Validate order
            is_valid, error = OrderValidator.validate_order(order)
            if not is_valid:
                order.status = OrderStatus.REJECTED
                order.error_message = error
                logger.error(f"Order validation failed: {error}")
                return False
            
            # Simulate order execution
            # In production, this would call actual broker/exchange API
            await self._submit_to_broker(order)
            
            # Update order status
            order.status = OrderStatus.SUBMITTED
            order.updated_at = datetime.utcnow()
            
            logger.info(f"Order {order.order_id} submitted successfully")
            return True
            
        except Exception as e:
            order.retry_count += 1
            order.error_message = str(e)
            logger.error(f"Error executing order {order.order_id}: {e}")
            
            if order.retry_count >= self.max_retries:
                order.status = OrderStatus.REJECTED
                logger.error(f"Order {order.order_id} rejected after {order.retry_count} retries")
                return False
            
            raise  # Re-raise to trigger retry
    
    async def _submit_to_broker(self, order: Order):
        """
        Submit order to broker/exchange
        Mock implementation for development
        """
        # Simulate network delay
        await asyncio.sleep(0.5)
        
        # Simulate order submission
        # In production, this would use broker API
        order.external_order_id = f"EXT-{order.order_id[:8]}"
        
        # Simulate execution
        if order.order_type == OrderType.MARKET:
            # Market orders fill immediately (in simulation)
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.average_price = order.price or 1.0500  # Mock price
            order.executed_at = datetime.utcnow()
        else:
            # Limit/Stop orders go to pending
            order.status = OrderStatus.SUBMITTED
        
        logger.debug(f"Order {order.order_id} submitted to broker with ID {order.external_order_id}")
    
    async def cancel_order(self, order: Order) -> bool:
        """Cancel an order"""
        try:
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                logger.warning(f"Cannot cancel order {order.order_id} in status {order.status}")
                return False
            
            # Simulate cancel request
            await asyncio.sleep(0.2)
            
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.utcnow()
            
            logger.info(f"Order {order.order_id} cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order {order.order_id}: {e}")
            return False


class OrderQueue:
    """Manage order queue with priority"""
    
    def __init__(self):
        self.queue: List[Order] = []
        self.processing = False
        self.executor = OrderExecutor()
    
    async def add_order(self, order: Order):
        """Add order to queue"""
        self.queue.append(order)
        logger.info(f"Order {order.order_id} added to queue. Queue size: {len(self.queue)}")
        
        # Start processing if not already running
        if not self.processing:
            asyncio.create_task(self.process_queue())
    
    async def process_queue(self):
        """Process orders in queue"""
        if self.processing:
            return
        
        self.processing = True
        logger.info("Starting order queue processing")
        
        try:
            while self.queue:
                order = self.queue.pop(0)
                
                try:
                    success = await self.executor.execute_order(order)
                    
                    if success:
                        logger.info(f"Order {order.order_id} executed successfully")
                    else:
                        logger.error(f"Order {order.order_id} execution failed")
                    
                    # Small delay between orders
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error processing order {order.order_id}: {e}")
                    order.status = OrderStatus.REJECTED
                    order.error_message = str(e)
        
        finally:
            self.processing = False
            logger.info("Order queue processing completed")
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return len(self.queue)
    
    def get_pending_orders(self) -> List[Order]:
        """Get all pending orders"""
        return [order for order in self.queue if order.status == OrderStatus.PENDING]


class OrderService:
    """
    Main order management service
    Handles order lifecycle and tracking
    """
    
    def __init__(self):
        self.queue = OrderQueue()
        self.orders: Dict[str, Order] = {}  # order_id -> Order
        self.user_orders: Dict[str, List[str]] = {}  # user_id -> [order_ids]
    
    async def create_order(
        self,
        user_id: str,
        symbol: str,
        order_type: OrderType,
        side: OrderSide,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> Order:
        """
        Create and submit a new order
        
        Args:
            user_id: User ID
            symbol: Trading symbol
            order_type: Type of order
            side: Buy or Sell
            quantity: Order quantity
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            
        Returns:
            Order object
        """
        # Create order
        order = Order(
            user_id=user_id,
            symbol=symbol,
            order_type=order_type,
            side=side,
            quantity=quantity,
            price=price,
            stop_price=stop_price
        )
        
        # Store order
        self.orders[order.order_id] = order
        
        # Track user orders
        if user_id not in self.user_orders:
            self.user_orders[user_id] = []
        self.user_orders[user_id].append(order.order_id)
        
        # Add to queue
        await self.queue.add_order(order)
        
        logger.info(f"Order created: {order.order_id} for user {user_id}")
        
        return order
    
    async def cancel_order(self, order_id: str, user_id: str) -> bool:
        """Cancel an order"""
        order = self.orders.get(order_id)
        
        if not order:
            logger.warning(f"Order {order_id} not found")
            return False
        
        if order.user_id != user_id:
            logger.warning(f"User {user_id} not authorized to cancel order {order_id}")
            return False
        
        return await self.queue.executor.cancel_order(order)
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_user_orders(self, user_id: str, status: Optional[OrderStatus] = None) -> List[Order]:
        """Get all orders for a user"""
        order_ids = self.user_orders.get(user_id, [])
        orders = [self.orders[oid] for oid in order_ids if oid in self.orders]
        
        if status:
            orders = [order for order in orders if order.status == status]
        
        return orders
    
    def get_active_orders(self, user_id: str) -> List[Order]:
        """Get active orders (pending, submitted, partially_filled)"""
        active_statuses = [
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.PARTIALLY_FILLED
        ]
        
        order_ids = self.user_orders.get(user_id, [])
        orders = [
            self.orders[oid]
            for oid in order_ids
            if oid in self.orders and self.orders[oid].status in active_statuses
        ]
        
        return orders
    
    async def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """Get current order status"""
        order = self.orders.get(order_id)
        return order.status if order else None
    
    def get_order_statistics(self, user_id: str) -> Dict:
        """Get order statistics for user"""
        orders = self.get_user_orders(user_id)
        
        total = len(orders)
        filled = sum(1 for o in orders if o.status == OrderStatus.FILLED)
        cancelled = sum(1 for o in orders if o.status == OrderStatus.CANCELLED)
        rejected = sum(1 for o in orders if o.status == OrderStatus.REJECTED)
        active = sum(1 for o in orders if o.status in [
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.PARTIALLY_FILLED
        ])
        
        return {
            'total_orders': total,
            'filled': filled,
            'cancelled': cancelled,
            'rejected': rejected,
            'active': active,
            'success_rate': (filled / total * 100) if total > 0 else 0
        }


# Global instance
order_service = OrderService()

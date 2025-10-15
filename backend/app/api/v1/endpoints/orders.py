"""
Order Management API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field

from app.core.auth import get_current_user, require_trader
from app.core.error_handlers import NotFoundError, ValidationError, AuthorizationError
from app.models.user import User
from app.services.order_service import (
    order_service,
    OrderType,
    OrderSide,
    OrderStatus
)
from app.services.signal_service import signal_service

router = APIRouter(tags=["orders"])


# Request/Response Models
class CreateOrderRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol")
    order_type: str = Field(..., description="Order type: market, limit, stop, stop_limit")
    side: str = Field(..., description="Order side: buy or sell")
    quantity: float = Field(..., gt=0, description="Order quantity")
    price: Optional[float] = Field(None, description="Limit price (for limit orders)")
    stop_price: Optional[float] = Field(None, description="Stop price (for stop orders)")
    take_profit: Optional[float] = Field(None, description="Take profit price")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    from_signal: bool = Field(False, description="Create order from signal")


class OrderResponse(BaseModel):
    order_id: str
    user_id: str
    symbol: str
    order_type: str
    side: str
    quantity: float
    price: Optional[float]
    stop_price: Optional[float]
    take_profit: Optional[float]
    stop_loss: Optional[float]
    status: str
    filled_quantity: float
    average_fill_price: float
    commission: float
    created_at: str
    updated_at: str
    executed_at: Optional[str]
    error_message: Optional[str]
    retry_count: int


class OrderListResponse(BaseModel):
    orders: List[dict]
    total: int


class OrderStatsResponse(BaseModel):
    total_orders: int
    active_orders: int
    historical_orders: int
    filled_orders: int
    failed_orders: int
    queue_size: int
    success_rate: float


@router.post("/orders", response_model=OrderResponse)
async def create_order(
    request: CreateOrderRequest,
    current_user: User = Depends(require_trader)
):
    """
    Create a new trading order
    
    Requires trader role.
    
    - **symbol**: Trading symbol (e.g., EUR/USD)
    - **order_type**: market, limit, stop, or stop_limit
    - **side**: buy or sell
    - **quantity**: Order size
    - **price**: Limit price (required for limit orders)
    - **stop_price**: Stop trigger price (required for stop orders)
    - **take_profit**: Take profit price
    - **stop_loss**: Stop loss price
    - **from_signal**: If true, uses current signal for take profit/stop loss
    """
    try:
        # Validate order type
        try:
            order_type_enum = OrderType(request.order_type.lower())
        except ValueError:
            raise ValidationError(f"Invalid order type: {request.order_type}")
        
        # Validate order side
        try:
            order_side_enum = OrderSide(request.side.lower())
        except ValueError:
            raise ValidationError(f"Invalid order side: {request.side}")
        
        # Get signal if requested
        signal = None
        if request.from_signal:
            signal = await signal_service.get_signal(request.symbol)
            if signal:
                # Use signal's take profit and stop loss if not provided
                if not request.take_profit:
                    request.take_profit = signal.take_profit
                if not request.stop_loss:
                    request.stop_loss = signal.stop_loss
        
        # Create order
        order = await order_service.create_order(
            user_id=current_user.id,
            symbol=request.symbol,
            order_type=order_type_enum,
            side=order_side_enum,
            quantity=request.quantity,
            price=request.price,
            stop_price=request.stop_price,
            take_profit=request.take_profit,
            stop_loss=request.stop_loss,
            signal=signal
        )
        
        return order.to_dict()
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get order details by ID
    
    - **order_id**: Order ID
    """
    order = order_service.get_order(order_id)
    
    if not order:
        raise NotFoundError(f"Order not found: {order_id}")
    
    # Check authorization
    if order.user_id != current_user.id and current_user.role != "admin":
        raise AuthorizationError("Not authorized to view this order")
    
    return order.to_dict()


@router.get("/orders", response_model=OrderListResponse)
async def get_user_orders(
    active_only: bool = Query(False, description="Return only active orders"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of orders to return"),
    current_user: User = Depends(get_current_user)
):
    """
    Get all orders for the current user
    
    - **active_only**: If true, only returns active (non-completed) orders
    - **limit**: Maximum number of orders to return (1-1000)
    """
    try:
        orders = order_service.get_user_orders(current_user.id, active_only)
        
        # Apply limit
        orders = orders[:limit]
        
        return {
            "orders": orders,
            "total": len(orders)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    current_user: User = Depends(require_trader)
):
    """
    Cancel an order
    
    Requires trader role.
    
    - **order_id**: Order ID to cancel
    """
    try:
        success = await order_service.cancel_order(order_id, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Order cannot be cancelled (not found or already completed)"
            )
        
        return {
            "message": "Order cancelled successfully",
            "order_id": order_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/stats/summary", response_model=OrderStatsResponse)
async def get_order_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get order statistics for the current user
    
    Returns statistics about user's orders including success rate.
    """
    try:
        # Get all orders for user
        user_orders = order_service.get_user_orders(current_user.id)
        
        # Calculate statistics
        total_orders = len(user_orders)
        active_orders = sum(1 for o in user_orders if o['status'] in ['pending', 'submitted'])
        filled_orders = sum(1 for o in user_orders if o['status'] == 'filled')
        failed_orders = sum(1 for o in user_orders if o['status'] == 'failed')
        
        success_rate = (filled_orders / total_orders * 100) if total_orders > 0 else 0
        
        return {
            "total_orders": total_orders,
            "active_orders": active_orders,
            "historical_orders": total_orders - active_orders,
            "filled_orders": filled_orders,
            "failed_orders": failed_orders,
            "queue_size": order_service.queue.get_queue_size(),
            "success_rate": round(success_rate, 2)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/stats/performance")
async def get_order_performance(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user)
):
    """
    Get order performance metrics
    
    - **days**: Number of days to analyze (1-365)
    """
    try:
        from datetime import datetime, timedelta
        
        # Get user orders
        user_orders = order_service.get_user_orders(current_user.id)
        
        # Filter by date
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_orders = [
            o for o in user_orders
            if datetime.fromisoformat(o['created_at'].replace('Z', '+00:00')) > cutoff_date
        ]
        
        # Calculate metrics
        filled_orders = [o for o in recent_orders if o['status'] == 'filled']
        
        total_volume = sum(o['filled_quantity'] * o['average_fill_price'] for o in filled_orders)
        total_commission = sum(o['commission'] for o in filled_orders)
        
        # Calculate profit/loss (simplified - would need actual position tracking)
        buy_orders = [o for o in filled_orders if o['side'] == 'buy']
        sell_orders = [o for o in filled_orders if o['side'] == 'sell']
        
        return {
            "period_days": days,
            "total_orders": len(recent_orders),
            "filled_orders": len(filled_orders),
            "buy_orders": len(buy_orders),
            "sell_orders": len(sell_orders),
            "total_volume": round(total_volume, 2),
            "total_commission": round(total_commission, 2),
            "avg_order_size": round(total_volume / len(filled_orders), 2) if filled_orders else 0,
            "success_rate": round(len(filled_orders) / len(recent_orders) * 100, 2) if recent_orders else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/from-signal/{symbol}")
async def create_order_from_signal(
    symbol: str,
    quantity: float = Query(..., gt=0, description="Order quantity"),
    current_user: User = Depends(require_trader)
):
    """
    Create an order directly from the current signal for a symbol
    
    Requires trader role.
    
    This is a convenience endpoint that:
    1. Gets the current signal for the symbol
    2. Validates the signal
    3. Creates a market order with signal's take profit and stop loss
    
    - **symbol**: Trading symbol
    - **quantity**: Order size
    """
    try:
        # Get signal
        signal = await signal_service.get_signal(symbol)
        
        if not signal:
            raise NotFoundError(f"No signal available for {symbol}")
        
        # Validate signal
        if not signal_service.validate_signal(signal):
            raise ValidationError("Signal is not valid for trading")
        
        # Determine order side from signal
        if signal.signal_type.value == "buy":
            order_side = OrderSide.BUY
        elif signal.signal_type.value == "sell":
            order_side = OrderSide.SELL
        else:
            raise ValidationError("Signal type is HOLD - no order created")
        
        # Create market order
        order = await order_service.create_order(
            user_id=current_user.id,
            symbol=symbol,
            order_type=OrderType.MARKET,
            side=order_side,
            quantity=quantity,
            take_profit=signal.take_profit,
            stop_loss=signal.stop_loss,
            signal=signal
        )
        
        return {
            "message": "Order created from signal",
            "order": order.to_dict(),
            "signal": signal.to_dict()
        }
        
    except (NotFoundError, ValidationError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""
Dashboard API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.models.user import User
from app.services.order_service import order_service
from app.services.signal_service import signal_service
from app.services.market_data_service import market_data_service

router = APIRouter(tags=["dashboard"])


# Response Models
class DashboardSummary(BaseModel):
    user_info: dict
    portfolio: dict
    orders: dict
    signals: dict
    market: dict
    activity: List[dict]


class PortfolioSummary(BaseModel):
    total_value: float
    cash_balance: float
    equity: float
    margin_used: float
    margin_available: float
    profit_loss: float
    profit_loss_pct: float
    open_positions: int


@router.get("/dashboard/summary", response_model=Dict)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user)
):
    """
    Get complete dashboard summary for the current user
    
    Includes:
    - User information
    - Portfolio summary
    - Order statistics
    - Signal statistics
    - Market overview
    - Recent activity
    """
    try:
        # Get user orders
        user_orders = order_service.get_user_orders(current_user.id)
        active_orders = [o for o in user_orders if o['status'] in ['pending', 'submitted']]
        filled_orders = [o for o in user_orders if o['status'] == 'filled']
        
        # Calculate portfolio metrics (simplified)
        total_volume = sum(
            o['filled_quantity'] * o['average_fill_price']
            for o in filled_orders
        )
        total_commission = sum(o['commission'] for o in filled_orders)
        
        # Get signal stats
        signal_history = signal_service.get_signal_history(None, 100)
        buy_signals = sum(1 for s in signal_history if s['signal_type'] == 'buy')
        sell_signals = sum(1 for s in signal_history if s['signal_type'] == 'sell')
        
        # Get market overview for watchlist
        watchlist_symbols = ["EUR/USD", "GBP/USD", "USD/JPY", "XAU/USD"]
        market_overview = []
        
        for symbol in watchlist_symbols:
            try:
                price_data = await market_data_service.get_current_price(symbol)
                market_overview.append({
                    "symbol": symbol,
                    "price": price_data['price'],
                    "change_24h": price_data['ohlc']['close'] - price_data['ohlc']['open']
                })
            except:
                pass
        
        # Recent activity (last 10 orders)
        recent_activity = []
        for order in user_orders[:10]:
            recent_activity.append({
                "type": "order",
                "action": f"{order['side'].upper()} {order['symbol']}",
                "status": order['status'],
                "quantity": order['quantity'],
                "price": order['average_fill_price'] if order['status'] == 'filled' else order['price'],
                "timestamp": order['created_at']
            })
        
        return {
            "user_info": {
                "user_id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "role": current_user.role,
                "created_at": current_user.created_at.isoformat() if hasattr(current_user, 'created_at') else None
            },
            "portfolio": {
                "total_value": round(10000 + total_volume, 2),  # Mock: Starting balance + volume
                "cash_balance": round(10000 - total_volume, 2),
                "equity": round(total_volume, 2),
                "margin_used": round(total_volume * 0.1, 2),  # 10% margin
                "margin_available": round(9000, 2),
                "profit_loss": round(-total_commission, 2),  # Simplified
                "profit_loss_pct": round(-total_commission / 10000 * 100, 2),
                "open_positions": len(active_orders)
            },
            "orders": {
                "total": len(user_orders),
                "active": len(active_orders),
                "filled": len(filled_orders),
                "success_rate": round(len(filled_orders) / len(user_orders) * 100, 2) if user_orders else 0
            },
            "signals": {
                "total": len(signal_history),
                "buy_signals": buy_signals,
                "sell_signals": sell_signals,
                "active_signals": len(signal_service.active_signals)
            },
            "market": {
                "watchlist": market_overview,
                "total_symbols": len(watchlist_symbols)
            },
            "activity": recent_activity
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/portfolio", response_model=Dict)
async def get_portfolio_details(
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed portfolio information
    
    Includes:
    - Account balance
    - Open positions
    - Profit/Loss breakdown
    - Risk metrics
    """
    try:
        # Get user orders
        user_orders = order_service.get_user_orders(current_user.id)
        filled_orders = [o for o in user_orders if o['status'] == 'filled']
        active_orders = [o for o in user_orders if o['status'] in ['pending', 'submitted']]
        
        # Calculate positions by symbol
        positions = {}
        for order in filled_orders:
            symbol = order['symbol']
            if symbol not in positions:
                positions[symbol] = {
                    "symbol": symbol,
                    "quantity": 0,
                    "avg_price": 0,
                    "current_value": 0,
                    "profit_loss": 0
                }
            
            # Update position (simplified - should track buy/sell separately)
            if order['side'] == 'buy':
                positions[symbol]['quantity'] += order['filled_quantity']
            else:
                positions[symbol]['quantity'] -= order['filled_quantity']
            
            positions[symbol]['avg_price'] = order['average_fill_price']
        
        # Get current prices and calculate P/L
        for symbol, position in positions.items():
            try:
                current_price_data = await market_data_service.get_current_price(symbol)
                current_price = current_price_data['price']
                
                position['current_value'] = position['quantity'] * current_price
                position['profit_loss'] = (current_price - position['avg_price']) * position['quantity']
            except:
                pass
        
        # Calculate totals
        total_value = sum(p['current_value'] for p in positions.values())
        total_pl = sum(p['profit_loss'] for p in positions.values())
        
        # Risk metrics
        cash_balance = 10000  # Mock starting balance
        equity = cash_balance + total_value
        margin_used = total_value * 0.1  # 10% margin
        margin_available = equity - margin_used
        
        return {
            "account": {
                "cash_balance": round(cash_balance, 2),
                "equity": round(equity, 2),
                "margin_used": round(margin_used, 2),
                "margin_available": round(margin_available, 2),
                "margin_level": round((equity / margin_used * 100), 2) if margin_used > 0 else 0
            },
            "positions": list(positions.values()),
            "summary": {
                "total_value": round(total_value, 2),
                "total_profit_loss": round(total_pl, 2),
                "total_profit_loss_pct": round((total_pl / cash_balance * 100), 2) if cash_balance > 0 else 0,
                "open_positions": len([p for p in positions.values() if p['quantity'] != 0]),
                "active_orders": len(active_orders)
            },
            "risk_metrics": {
                "exposure": round(total_value, 2),
                "exposure_pct": round((total_value / equity * 100), 2) if equity > 0 else 0,
                "available_margin_pct": round((margin_available / equity * 100), 2) if equity > 0 else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/activity")
async def get_activity_feed(
    limit: int = Query(50, ge=1, le=200, description="Number of activities to return"),
    activity_type: str = Query(None, description="Filter by type: orders, signals, trades"),
    current_user: User = Depends(get_current_user)
):
    """
    Get user activity feed
    
    - **limit**: Number of activities (1-200)
    - **activity_type**: Filter by type (orders, signals, trades)
    """
    try:
        activities = []
        
        # Get orders activity
        if not activity_type or activity_type == "orders":
            user_orders = order_service.get_user_orders(current_user.id)
            
            for order in user_orders[:limit]:
                activities.append({
                    "id": order['order_id'],
                    "type": "order",
                    "action": f"{order['side'].upper()} {order['symbol']}",
                    "description": f"{order['order_type'].title()} order for {order['quantity']} {order['symbol']}",
                    "status": order['status'],
                    "details": {
                        "symbol": order['symbol'],
                        "side": order['side'],
                        "quantity": order['quantity'],
                        "price": order['average_fill_price'] if order['status'] == 'filled' else order['price'],
                        "commission": order['commission']
                    },
                    "timestamp": order['created_at']
                })
        
        # Get signals activity
        if not activity_type or activity_type == "signals":
            signal_history = signal_service.get_signal_history(None, limit)
            
            for signal in signal_history:
                activities.append({
                    "id": signal['timestamp'],
                    "type": "signal",
                    "action": f"{signal['signal_type'].upper()} signal for {signal['symbol']}",
                    "description": f"{signal['strength'].title()} {signal['signal_type']} signal (confidence: {signal['confidence']:.1%})",
                    "status": "active",
                    "details": {
                        "symbol": signal['symbol'],
                        "signal_type": signal['signal_type'],
                        "strength": signal['strength'],
                        "confidence": signal['confidence'],
                        "entry_price": signal['entry_price']
                    },
                    "timestamp": signal['timestamp']
                })
        
        # Sort by timestamp (most recent first)
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Apply limit
        activities = activities[:limit]
        
        return {
            "activities": activities,
            "total": len(activities),
            "filters": {
                "type": activity_type,
                "limit": limit
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/performance")
async def get_performance_metrics(
    period_days: int = Query(30, ge=1, le=365, description="Analysis period in days"),
    current_user: User = Depends(get_current_user)
):
    """
    Get trading performance metrics
    
    - **period_days**: Analysis period (1-365 days)
    """
    try:
        # Get orders for the period
        cutoff_date = datetime.utcnow() - timedelta(days=period_days)
        user_orders = order_service.get_user_orders(current_user.id)
        
        period_orders = [
            o for o in user_orders
            if datetime.fromisoformat(o['created_at'].replace('Z', '+00:00')) > cutoff_date
        ]
        
        filled_orders = [o for o in period_orders if o['status'] == 'filled']
        
        # Calculate metrics
        total_orders = len(period_orders)
        total_filled = len(filled_orders)
        total_volume = sum(o['filled_quantity'] * o['average_fill_price'] for o in filled_orders)
        total_commission = sum(o['commission'] for o in filled_orders)
        
        # Win rate (simplified - would need actual P/L tracking)
        winning_trades = len([o for o in filled_orders if o['side'] == 'sell'])  # Mock
        win_rate = (winning_trades / total_filled * 100) if total_filled > 0 else 0
        
        # Trading frequency
        trading_days = period_days
        avg_trades_per_day = total_orders / trading_days if trading_days > 0 else 0
        
        return {
            "period_days": period_days,
            "orders": {
                "total": total_orders,
                "filled": total_filled,
                "success_rate": round((total_filled / total_orders * 100), 2) if total_orders > 0 else 0
            },
            "volume": {
                "total": round(total_volume, 2),
                "average_per_trade": round(total_volume / total_filled, 2) if total_filled > 0 else 0
            },
            "costs": {
                "total_commission": round(total_commission, 2),
                "avg_commission_per_trade": round(total_commission / total_filled, 2) if total_filled > 0 else 0
            },
            "performance": {
                "win_rate": round(win_rate, 2),
                "profit_factor": 1.5,  # Mock
                "sharpe_ratio": 1.2,  # Mock
                "max_drawdown": 5.0  # Mock
            },
            "activity": {
                "trading_days": trading_days,
                "avg_trades_per_day": round(avg_trades_per_day, 2),
                "most_traded_symbol": "EUR/USD"  # Mock
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

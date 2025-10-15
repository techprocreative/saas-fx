from typing import Any, List, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, or_
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models import (
    User, TradingAccount, AIStrategy, Trade, Commission,
    ConnectionStatus, OrderType, TradeStatus
)
from app.api.v1.endpoints.auth import get_current_user
from pydantic import BaseModel

router = APIRouter()

# Pydantic models
class DashboardStats(BaseModel):
    total_accounts: int
    online_accounts: int
    active_strategies: int
    open_trades: int
    total_profit_loss: float
    todays_trades: int
    commission_earned: float

class PerformanceMetrics(BaseModel):
    total_trades: int
    win_rate: float
    average_profit: float
    sharpe_ratio: float
    max_drawdown: float
    profit_factor: float

class TradeAnalytics(BaseModel):
    period_days: int
    trades: List[dict]
    metrics: PerformanceMetrics

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get comprehensive dashboard analytics"""
    
    # Get user's trading accounts
    accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id
    ).all()
    
    total_accounts = len(accounts)
    online_accounts = sum(1 for acc in accounts if acc.connection_status == ConnectionStatus.ONLINE)
    
    # Get active strategies
    active_strategies = db.query(AIStrategy).filter(
        and_(
            AIStrategy.user_id == current_user.id,
            AIStrategy.status == 'active'
        )
    ).count()
    
    # Get open trades
    open_trades = db.query(Trade).join(TradingAccount).filter(
        and_(
            TradingAccount.user_id == current_user.id,
            Trade.status == TradeStatus.OPEN
        )
    ).count()
    
    # Calculate total profit/loss
    total_pl_result = db.query(func.coalesce(func.sum(Trade.profit_loss), 0)).join(TradingAccount).filter(
        TradingAccount.user_id == current_user.id
    ).scalar()
    total_profit_loss = float(total_pl_result) if total_pl_result else 0.0
    
    # Get today's trades
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    todays_trades = db.query(Trade).join(TradingAccount).filter(
        and_(
            TradingAccount.user_id == current_user.id,
            Trade.opened_at >= today_start
        )
    ).count()
    
    # Get commission summary
    commission_result = db.query(func.coalesce(func.sum(Commission.amount), 0)).filter(
        and_(
            Commission.user_id == current_user.id,
            Commission.status == 'processed'
        )
    ).scalar()
    commission_earned = float(commission_result) if commission_result else 0.0
    
    return DashboardStats(
        total_accounts=total_accounts,
        online_accounts=online_accounts,
        active_strategies=active_strategies,
        open_trades=open_trades,
        total_profit_loss=total_profit_loss,
        todays_trades=todays_trades,
        commission_earned=commission_earned
    )

@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics(
    period_days: int = Query(default=30, description="Period in days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get trading performance metrics"""
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=period_days)
    
    # Get trades in period
    trades = db.query(Trade).join(TradingAccount).filter(
        and_(
            TradingAccount.user_id == current_user.id,
            Trade.opened_at >= start_date,
            Trade.opened_at <= end_date,
            Trade.status == TradeStatus.CLOSED,
            Trade.profit_loss.isnot(None)
        )
    ).all()
    
    if not trades:
        return PerformanceMetrics(
            total_trades=0,
            win_rate=0.0,
            average_profit=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            profit_factor=0.0
        )
    
    # Calculate metrics
    total_trades = len(trades)
    winning_trades = [t for t in trades if t.profit_loss > 0]
    win_rate = (len(winning_trades) / total_trades) * 100
    
    # Average profit
    total_profit = sum(t.profit_loss for t in trades)
    average_profit = total_profit / total_trades
    
    # Sharpe ratio (simplified)
    returns = [t.profit_loss for t in trades]
    import statistics
    mean_return = statistics.mean(returns) if returns else 0
    return_std = statistics.stdev(returns) if len(returns) > 1 else 1
    sharpe_ratio = (mean_return / return_std) * (252**0.5) if return_std != 0 else 0  # Annualized
    
    # Max drawdown (simplified calculation)
    cumulative_returns = []
    running_total = 0
    for profit in returns:
        running_total += profit
        cumulative_returns.append(running_total)
    
    max_drawdown = 0
    peak = cumulative_returns[0] if cumulative_returns else 0
    for value in cumulative_returns:
        if value > peak:
            peak = value
        drawdown = peak - value
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    # Profit factor
    gross_profit = sum(t.profit_loss for t in winning_trades)
    losing_trades = [t for t in trades if t.profit_loss < 0]
    gross_loss = abs(sum(t.profit_loss for t in losing_trades))
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
    
    return PerformanceMetrics(
        total_trades=total_trades,
        win_rate=win_rate,
        average_profit=average_profit,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        profit_factor=profit_factor
    )

@router.get("/trades")
async def get_trade_analytics(
    period_days: int = Query(default=30, description="Period in days"),
    symbol: str = Query(default=None, description="Filter by symbol"),
    strategy_id: str = Query(default=None, description="Filter by strategy"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get detailed trade analytics with filters"""
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=period_days)
    
    # Build query
    query = db.query(Trade).join(TradingAccount).filter(
        and_(
            TradingAccount.user_id == current_user.id,
            Trade.opened_at >= start_date,
            Trade.opened_at <= end_date
        )
    )
    
    # Apply filters
    if symbol:
        query = query.filter(Trade.symbol == symbol)
    
    if strategy_id:
        query = query.filter(Trade.strategy_id == strategy_id)
    
    trades = query.order_by(Trade.opened_at.desc()).all()
    
    return {
        "trades": [
            {
                "id": str(trade.id),
                "symbol": trade.symbol,
                "type": trade.type.value,
                "volume": float(trade.volume),
                "open_price": float(trade.open_price),
                "close_price": float(trade.close_price) if trade.close_price else None,
                "stop_loss": float(trade.stop_loss) if trade.stop_loss else None,
                "take_profit": float(trade.take_profit) if trade.take_profit else None,
                "profit_loss": float(trade.profit_loss),
                "commission": float(trade.commission),
                "status": trade.status.value,
                "opened_at": trade.opened_at.isoformat(),
                "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
                "strategy_name": trade.strategy.name if trade.strategy else None
            }
            for trade in trades
        ],
        "summary": {
            "total_trades": len(trades),
            "winning_trades": len([t for t in trades if t.profit_loss > 0]),
            "total_profit_loss": sum(t.profit_loss for t in trades),
            "total_commission": sum(t.commission for t in trades)
        },
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": period_days
        }
    }

@router.get("/commissions")
async def get_commission_analytics(
    period_days: int = Query(default=30, description="Period in days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get commission analytics and breakdown"""
    
    from app.services.commission_service import commission_settlement
    
    # Get commission summary
    summary = await commission_settlement.get_user_commission_summary(
        user_id=str(current_user.id),
        period_days=period_days
    )
    
    return summary

@router.get("/strategies/{strategy_id}/performance")
async def get_strategy_performance(
    strategy_id: str,
    period_days: int = Query(default=30, description="Period in days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get performance analytics for specific strategy"""
    
    # Verify strategy belongs to user
    strategy = db.query(AIStrategy).filter(
        and_(
            AIStrategy.id == strategy_id,
            AIStrategy.user_id == current_user.id
        )
    ).first()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=period_days)
    
    # Get trades for this strategy
    trades = db.query(Trade).filter(
        and_(
            Trade.strategy_id == strategy_id,
            Trade.opened_at >= start_date,
            Trade.opened_at <= end_date,
            Trade.status == TradeStatus.CLOSED
        )
    ).all()
    
    # Calculate strategy-specific metrics
    total_trades = len(trades)
    winning_trades = [t for t in trades if t.profit_loss > 0]
    win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
    
    total_profit_loss = sum(t.profit_loss for t in trades)
    average_profit = total_profit_loss / total_trades if total_trades > 0 else 0
    
    return {
        "strategy": {
            "id": str(strategy.id),
            "name": strategy.name,
            "llm_model": strategy.llm_model,
            "status": strategy.status
        },
        "performance": {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_profit_loss": float(total_profit_loss),
            "average_profit": average_profit,
            "max_profit": max([t.profit_loss for t in trades]) if trades else 0,
            "max_loss": min([t.profit_loss for t in trades]) if trades else 0
        },
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": period_days
        }
    }

@router.get("/real-time")
async def get_real_time_updates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get real-time trading data"""
    
    # Get current positions
    open_trades = db.query(Trade).join(TradingAccount).filter(
        and_(
            TradingAccount.user_id == current_user.id,
            Trade.status == TradeStatus.OPEN
        )
    ).all()
    
    # Get account balances
    accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id
    ).all()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "open_positions": [
            {
                "id": str(trade.id),
                "symbol": trade.symbol,
                "type": trade.type.value,
                "volume": float(trade.volume),
                "open_price": float(trade.open_price),
                "current_profit": float(trade.profit_loss) if trade.profit_loss else 0,
                "opened_at": trade.opened_at.isoformat(),
                "strategy_name": trade.strategy.name if trade.strategy else None
            }
            for trade in open_trades
        ],
        "accounts": [
            {
                "id": str(account.id),
                "mt5_login": account.mt5_login,
                "broker": account.broker,
                "balance": float(account.balance) if account.balance else 0,
                "connection_status": account.connection_status.value if account.connection_status else "offline",
                "last_ping": account.last_ping.isoformat() if account.last_ping else None
            }
            for account in accounts
        ],
        "active_strategies": db.query(AIStrategy).filter(
            and_(
                AIStrategy.user_id == current_user.id,
                AIStrategy.status == 'active'
            )
        ).count()
    }

@router.get("/export/performance")
async def export_performance_data(
    format: str = Query(default="json", enum=["json", "csv"]),
    period_days: int = Query(default=30, description="Period in days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Export performance data in specified format"""
    
    # Get trade data
    trades = db.query(Trade).join(TradingAccount).filter(
        and_(
            TradingAccount.user_id == current_user.id,
            Trade.opened_at >= datetime.utcnow() - timedelta(days=period_days)
        )
    ).all()
    
    if format == "csv":
        # Generate CSV data
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'ID', 'Symbol', 'Type', 'Volume', 'Open Price', 
            'Close Price', 'Stop Loss', 'Take Profit', 
            'Profit/Loss', 'Commission', 'Status', 
            'Opened At', 'Closed At', 'Strategy'
        ])
        
        # Data rows
        for trade in trades:
            writer.writerow([
                trade.id, trade.symbol, trade.type.value, trade.volume,
                trade.open_price, trade.close_price, trade.stop_loss, 
                trade.take_profit, trade.profit_loss, trade.commission,
                trade.status.value, trade.opened_at.isoformat(),
                trade.closed_at.isoformat() if trade.closed_at else '',
                trade.strategy.name if trade.strategy else ''
            ])
        
        csv_data = output.getvalue()
        output.close()
        
        return {
            "data": csv_data,
            "format": "csv",
            "filename": f"performance_export_{current_user.username}_{period_days}days.csv"
        }
    
    else:  # JSON format
        return {
            "data": [
                {
                    "id": str(trade.id),
                    "symbol": trade.symbol,
                    "type": trade.type.value,
                    "volume": float(trade.volume),
                    "open_price": float(trade.open_price),
                    "close_price": float(trade.close_price) if trade.close_price else None,
                    "stop_loss": float(trade.stop_loss) if trade.stop_loss else None,
                    "take_profit": float(trade.take_profit) if trade.take_profit else None,
                    "profit_loss": float(trade.profit_loss),
                    "commission": float(trade.commission),
                    "status": trade.status.value,
                    "opened_at": trade.opened_at.isoformat(),
                    "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
                    "strategy_name": trade.strategy.name if trade.strategy else None
                }
                for trade in trades
            ],
            "format": "json",
            "filename": f"performance_export_{current_user.username}_{period_days}days.json"
        }

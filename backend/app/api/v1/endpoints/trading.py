from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import (
    User, TradingAccount, AIStrategy, Trade, Commission,
    ConnectionStatus, OrderType, TradeStatus
)
from app.api.v1.endpoints.auth import get_current_user
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter()

# Pydantic models
class TradingAccountCreate(BaseModel):
    mt5_login: str
    broker: str
    account_type: str = "standard"

class TradingAccountResponse(BaseModel):
    id: str
    mt5_login: str
    broker: str
    account_type: str
    balance: float
    connection_status: str
    websocket_connection_id: str = None
    pytrader_ea_version: str = None
    last_ping: str = None
    created_at: str

class StrategyCreate(BaseModel):
    name: str
    llm_model: str = "claude-3-opus"
    user_preferences: dict = {}
    market_conditions: dict = {}

class StrategyResponse(BaseModel):
    id: str
    name: str
    llm_model: str
    strategy_config: dict = {}
    performance_metrics: dict = {}
    status: str
    created_at: str

class TradingConfig(BaseModel):
    strategy_id: str
    account_id: str
    is_active: bool = True
    risk_settings: dict = {}

@router.get("/accounts", response_model=List[TradingAccountResponse])
async def get_trading_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get user's trading accounts"""
    accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id
    ).all()
    
    return [
        TradingAccountResponse(
            id=str(account.id),
            mt5_login=account.mt5_login,
            broker=account.broker,
            account_type=account.account_type or "standard",
            balance=float(account.balance) if account.balance else 0.0,
            connection_status=account.connection_status.value if account.connection_status else "offline",
            websocket_connection_id=account.websocket_connection_id,
            pytrader_ea_version=account.pytrader_ea_version,
            last_ping=account.last_ping.isoformat() if account.last_ping else None,
            created_at=account.created_at.isoformat()
        )
        for account in accounts
    ]

@router.post("/accounts", response_model=TradingAccountResponse)
async def create_trading_account(
    account_data: TradingAccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create new trading account"""
    # Check if account already exists
    existing = db.query(TradingAccount).filter(
        TradingAccount.mt5_login == account_data.mt5_login,
        TradingAccount.user_id == current_user.id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account already exists"
        )
    
    account = TradingAccount(
        user_id=current_user.id,
        mt5_login=account_data.mt5_login,
        broker=account_data.broker,
        account_type=account_data.account_type,
        connection_status=ConnectionStatus.OFFLINE
    )
    
    db.add(account)
    db.commit()
    db.refresh(account)
    
    # Generate user EA package
    from app.services.user_onboarding import UserOnboardingService
    onboarding = UserOnboardingService()
    await onboarding.generate_ea_for_user(current_user.id, account.id)
    
    return TradingAccountResponse(
        id=str(account.id),
        mt5_login=account.mt5_login,
        broker=account.broker,
        account_type=account.account_type,
        balance=float(account.balance) if account.balance else 0.0,
        connection_status=account.connection_status.value,
        websocket_connection_id=account.websocket_connection_id,
        pytrader_ea_version=account.pytrader_ea_version,
        last_ping=account.last_ping.isoformat() if account.last_ping else None,
        created_at=account.created_at.isoformat()
    )

@router.get("/strategies", response_model=List[StrategyResponse])
async def get_strategies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get user's AI strategies"""
    strategies = db.query(AIStrategy).filter(
        AIStrategy.user_id == current_user.id
    ).all()
    
    return [
        StrategyResponse(
            id=str(strategy.id),
            name=strategy.name,
            llm_model=strategy.llm_model or "claude-3-opus",
            strategy_config=eval(strategy.strategy_config) if strategy.strategy_config else {},
            performance_metrics=eval(strategy.performance_metrics) if strategy.performance_metrics else {},
            status=strategy.status,
            created_at=strategy.created_at.isoformat()
        )
        for strategy in strategies
    ]

@router.post("/strategies/generate", response_model=StrategyResponse)
async def generate_ai_strategy(
    strategy_data: StrategyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Generate AI trading strategy"""
    try:
        from app.services.ai_service import ai_strategy_generator
        
        # Generate strategy using AI
        user_preferences = {
            'risk_level': strategy_data.user_preferences.get('risk_level', 'medium'),
            'trading_style': strategy_data.user_preferences.get('trading_style', 'swing'),
            'timeframes': strategy_data.user_preferences.get('timeframes', ['H1', 'H4']),
            'max_risk_percent': strategy_data.user_preferences.get('max_risk_percent', 2.0),
            'preferred_pairs': strategy_data.user_preferences.get('preferred_pairs', ['EURUSD', 'GBPUSD'])
        }
        
        market_conditions = strategy_data.market_conditions or {
            'trend': 'neutral',
            'volatility': 'medium',
            'sentiment': 'neutral'
        }
        
        result = await ai_strategy_generator.generate_strategy(
            user_preferences=user_preferences,
            market_conditions=market_conditions,
            selected_model=strategy_data.llm_model
        )
        
        # Save strategy to database
        strategy = AIStrategy(
            user_id=current_user.id,
            name=strategy_data.name,
            llm_model=strategy_data.llm_model,
            strategy_config=str(result['freqtrade_config']),
            performance_metrics=result['strategy'].get('expected_performance', {}),
            status='active'
        )
        
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
        
        return StrategyResponse(
            id=str(strategy.id),
            name=strategy.name,
            llm_model=strategy.llm_model,
            strategy_config=result['freqtrade_config'],
            performance_metrics=result['strategy'].get('expected_performance', {}),
            status=strategy.status,
            created_at=strategy.created_at.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating strategy: {str(e)}"
        )

@router.post("/start")
async def start_trading(
    trading_config: TradingConfig,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Start automated trading"""
    # Verify strategy and account belong to user
    strategy = db.query(AIStrategy).filter(
        AIStrategy.id == trading_config.strategy_id,
        AIStrategy.user_id == current_user.id
    ).first()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    account = db.query(TradingAccount).filter(
        TradingAccount.id == trading_config.account_id,
        TradingAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trading account not found"
        )
    
    if account.connection_status != ConnectionStatus.ONLINE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trading account is not connected"
        )
    
    # Activate strategy (simplified - in production would update strategy status)
    strategy.status = 'active' if trading_config.is_active else 'inactive'
    db.commit()
    
    return {
        "message": "Trading started successfully",
        "strategy_id": trading_config.strategy_id,
        "account_id": trading_config.account_id,
        "status": "active"
    }

@router.post("/stop")
async def stop_trading(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Stop trading for strategy"""
    strategy = db.query(AIStrategy).filter(
        AIStrategy.id == strategy_id,
        AIStrategy.user_id == current_user.id
    ).first()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    strategy.status = 'inactive'
    db.commit()
    
    return {
        "message": "Trading stopped successfully",
        "strategy_id": strategy_id,
        "status": "inactive"
    }

@router.get("/trades", response_model=List[dict])
async def get_trades(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get user's trading history"""
    trades = db.query(Trade).join(TradingAccount).filter(
        TradingAccount.user_id == current_user.id
    ).order_by(Trade.opened_at.desc()).limit(limit).all()
    
    return [
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
            "mt5_order_id": trade.mt5_order_id,
            "mt5_position_id": trade.mt5_position_id,
            "opened_at": trade.opened_at.isoformat(),
            "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
            "strategy_name": trade.strategy.name if trade.strategy else None
        }
        for trade in trades
    ]

@router.get("/status")
async def get_trading_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get current trading status"""
    # Get accounts and their connection status
    accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id
    ).all()
    
    # Get active strategies
    active_strategies = db.query(AIStrategy).filter(
        AIStrategy.user_id == current_user.id,
        AIStrategy.status == "active"
    ).all()
    
    # Get recent trades
    recent_trades = db.query(Trade).join(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        Trade.status == TradeStatus.OPEN
    ).count()
    
    # Calculate total P&L
    total_pl = db.query(Trade).join(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        Trade.profit_loss.isnot(None)
    ).with_entities(Trade.profit_loss).all()
    
    total_profit_loss = sum([pl[0] for pl in total_pl]) if total_pl else 0
    
    return {
        "accounts": {
            "total": len(accounts),
            "online": sum(1 for acc in accounts if acc.connection_status == ConnectionStatus.ONLINE),
            "offline": sum(1 for acc in accounts if acc.connection_status == ConnectionStatus.OFFLINE)
        },
        "strategies": {
            "total": len(active_strategies),
            "active": len([s for s in active_strategies if s.status == "active"])
        },
        "trades": {
            "open_positions": recent_trades,
            "total_profit_loss": float(total_profit_loss)
        },
        "connection_status": "online" if any(acc.connection_status == ConnectionStatus.ONLINE for acc in accounts) else "offline"
    }

@router.get("/account/{account_id}/ea-download")
async def download_ea(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """Generate and download EA for account"""
    # Verify account belongs to user
    account = db.query(TradingAccount).filter(
        TradingAccount.id == account_id,
        TradingAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Generate EA package
    from app.services.user_onboarding import UserOnboardingService
    onboarding = UserOnboardingService()
    package_path = await onboarding.generate_ea_for_user(current_user.id, account_id)
    
    return {
        "download_url": f"{settings.EA_DOWNLOAD_URL.format(user_id=current_user.id)}",
        "setup_guide": f"{settings.SETUP_GUIDE_URL.format(user_token=current_user.id)}",
        "package_path": package_path
    }

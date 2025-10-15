"""
Trading Signals API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

from app.core.auth import get_current_user, require_trader
from app.core.error_handlers import NotFoundError, ValidationError
from app.models.user import User
from app.services.signal_service import signal_service, SignalType, SignalStrength

router = APIRouter(tags=["signals"])


# Request/Response Models
class SignalResponse(BaseModel):
    symbol: str
    signal_type: str
    strength: str
    confidence: float
    entry_price: float
    take_profit: Optional[float]
    stop_loss: Optional[float]
    indicators: dict
    timestamp: str


class SignalBatchRequest(BaseModel):
    symbols: List[str]


class SignalHistoryResponse(BaseModel):
    signals: List[dict]
    total: int


@router.get("/signals/{symbol}", response_model=SignalResponse)
async def get_signal(
    symbol: str,
    force_regenerate: bool = Query(False, description="Force signal regeneration"),
    current_user: User = Depends(get_current_user)
):
    """
    Get trading signal for a specific symbol
    
    - **symbol**: Trading symbol (e.g., EUR/USD, XAU/USD)
    - **force_regenerate**: Force new signal generation (ignores cache)
    """
    try:
        signal = await signal_service.get_signal(symbol, force_regenerate)
        
        if not signal:
            raise NotFoundError(f"No signal available for {symbol}")
        
        return signal.to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/signals/batch", response_model=List[SignalResponse])
async def get_signals_batch(
    request: SignalBatchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Get trading signals for multiple symbols
    
    - **symbols**: List of trading symbols
    """
    if not request.symbols:
        raise ValidationError("Symbols list cannot be empty")
    
    if len(request.symbols) > 20:
        raise ValidationError("Maximum 20 symbols per request")
    
    try:
        signals = await signal_service.get_signals_batch(request.symbols)
        
        return [signal.to_dict() for signal in signals.values()]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/{symbol}/history", response_model=SignalHistoryResponse)
async def get_signal_history(
    symbol: str,
    limit: int = Query(100, ge=1, le=1000, description="Number of signals to return"),
    current_user: User = Depends(get_current_user)
):
    """
    Get signal history for a specific symbol
    
    - **symbol**: Trading symbol
    - **limit**: Number of historical signals (1-1000)
    """
    try:
        history = signal_service.get_signal_history(symbol, limit)
        
        return {
            "signals": history,
            "total": len(history)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals", response_model=SignalHistoryResponse)
async def get_all_signals_history(
    limit: int = Query(100, ge=1, le=1000, description="Number of signals to return"),
    current_user: User = Depends(get_current_user)
):
    """
    Get signal history for all symbols
    
    - **limit**: Number of historical signals (1-1000)
    """
    try:
        history = signal_service.get_signal_history(None, limit)
        
        return {
            "signals": history,
            "total": len(history)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/{symbol}/validate")
async def validate_signal(
    symbol: str,
    current_user: User = Depends(require_trader)
):
    """
    Validate the current signal for a symbol
    
    Requires trader role.
    
    - **symbol**: Trading symbol
    """
    try:
        signal = await signal_service.get_signal(symbol)
        
        if not signal:
            raise NotFoundError(f"No signal available for {symbol}")
        
        is_valid = signal_service.validate_signal(signal)
        
        return {
            "symbol": symbol,
            "signal": signal.to_dict(),
            "is_valid": is_valid,
            "validation_details": {
                "confidence_check": signal.confidence >= 0.6,
                "age_check": True,  # Already checked in validate_signal
                "risk_management": signal.take_profit and signal.stop_loss
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/stats/summary")
async def get_signal_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get signal statistics summary
    """
    try:
        history = signal_service.get_signal_history(None, 1000)
        
        total_signals = len(history)
        
        # Count by signal type
        buy_signals = sum(1 for s in history if s['signal_type'] == 'buy')
        sell_signals = sum(1 for s in history if s['signal_type'] == 'sell')
        hold_signals = sum(1 for s in history if s['signal_type'] == 'hold')
        
        # Count by strength
        strong_signals = sum(1 for s in history if s['strength'] == 'strong')
        moderate_signals = sum(1 for s in history if s['strength'] == 'moderate')
        weak_signals = sum(1 for s in history if s['strength'] == 'weak')
        
        # Average confidence
        avg_confidence = sum(s['confidence'] for s in history) / total_signals if total_signals > 0 else 0
        
        return {
            "total_signals": total_signals,
            "by_type": {
                "buy": buy_signals,
                "sell": sell_signals,
                "hold": hold_signals
            },
            "by_strength": {
                "strong": strong_signals,
                "moderate": moderate_signals,
                "weak": weak_signals
            },
            "average_confidence": round(avg_confidence, 2),
            "active_signals": len(signal_service.active_signals)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

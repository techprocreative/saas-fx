"""
Market Data API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.auth import get_current_user
from app.core.error_handlers import NotFoundError, ValidationError
from app.models.user import User
from app.services.market_data_service import market_data_service

router = APIRouter(tags=["market-data"])


# Response Models
class PriceResponse(BaseModel):
    symbol: str
    price: float
    bid: float
    ask: float
    volume: float
    timestamp: str
    ohlc: dict


class HistoricalDataResponse(BaseModel):
    symbol: str
    timeframe: str
    data: List[dict]
    total: int


class SymbolInfo(BaseModel):
    symbol: str
    name: str
    category: str
    base_currency: str
    quote_currency: str
    available: bool


@router.get("/market-data/symbols", response_model=List[SymbolInfo])
async def get_available_symbols(
    category: Optional[str] = Query(None, description="Filter by category (forex, crypto, commodities)"),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of available trading symbols
    
    - **category**: Optional filter by category
    """
    # Available symbols (in production, this would come from broker API)
    symbols = [
        {
            "symbol": "EUR/USD",
            "name": "Euro / US Dollar",
            "category": "forex",
            "base_currency": "EUR",
            "quote_currency": "USD",
            "available": True
        },
        {
            "symbol": "GBP/USD",
            "name": "British Pound / US Dollar",
            "category": "forex",
            "base_currency": "GBP",
            "quote_currency": "USD",
            "available": True
        },
        {
            "symbol": "USD/JPY",
            "name": "US Dollar / Japanese Yen",
            "category": "forex",
            "base_currency": "USD",
            "quote_currency": "JPY",
            "available": True
        },
        {
            "symbol": "AUD/USD",
            "name": "Australian Dollar / US Dollar",
            "category": "forex",
            "base_currency": "AUD",
            "quote_currency": "USD",
            "available": True
        },
        {
            "symbol": "USD/CAD",
            "name": "US Dollar / Canadian Dollar",
            "category": "forex",
            "base_currency": "USD",
            "quote_currency": "CAD",
            "available": True
        },
        {
            "symbol": "XAU/USD",
            "name": "Gold / US Dollar",
            "category": "commodities",
            "base_currency": "XAU",
            "quote_currency": "USD",
            "available": True
        },
        {
            "symbol": "XAG/USD",
            "name": "Silver / US Dollar",
            "category": "commodities",
            "base_currency": "XAG",
            "quote_currency": "USD",
            "available": True
        },
        {
            "symbol": "BTC/USD",
            "name": "Bitcoin / US Dollar",
            "category": "crypto",
            "base_currency": "BTC",
            "quote_currency": "USD",
            "available": True
        },
        {
            "symbol": "ETH/USD",
            "name": "Ethereum / US Dollar",
            "category": "crypto",
            "base_currency": "ETH",
            "quote_currency": "USD",
            "available": True
        }
    ]
    
    # Filter by category if provided
    if category:
        symbols = [s for s in symbols if s["category"] == category.lower()]
    
    return symbols


@router.get("/market-data/{symbol}/current", response_model=PriceResponse)
async def get_current_price(
    symbol: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get current price for a trading symbol
    
    - **symbol**: Trading symbol (e.g., EUR/USD, XAU/USD, BTC/USD)
    """
    try:
        # Get current price from market data service
        price_data = await market_data_service.get_current_price(symbol)
        
        if not price_data:
            raise NotFoundError(f"No price data available for {symbol}")
        
        return {
            "symbol": price_data['symbol'],
            "price": price_data['price'],
            "bid": price_data['bid'],
            "ask": price_data['ask'],
            "volume": price_data['volume'],
            "timestamp": price_data['timestamp'].isoformat(),
            "ohlc": price_data['ohlc']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-data/{symbol}/historical", response_model=HistoricalDataResponse)
async def get_historical_data(
    symbol: str,
    timeframe: str = Query("1h", description="Timeframe: 1m, 5m, 15m, 1h, 4h, 1d"),
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
    current_user: User = Depends(get_current_user)
):
    """
    Get historical OHLCV data for a symbol
    
    - **symbol**: Trading symbol
    - **timeframe**: Data timeframe (1m, 5m, 15m, 1h, 4h, 1d)
    - **days**: Number of days of historical data (1-365)
    """
    try:
        # Validate timeframe
        valid_timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
        if timeframe not in valid_timeframes:
            raise ValidationError(f"Invalid timeframe. Valid options: {', '.join(valid_timeframes)}")
        
        # Get historical data
        data = await market_data_service.get_historical_data(
            symbol=symbol,
            timeframe=timeframe,
            days=days
        )
        
        if not data:
            raise NotFoundError(f"No historical data available for {symbol}")
        
        # Format response
        formatted_data = []
        for candle in data:
            formatted_data.append({
                "timestamp": candle['timestamp'].isoformat(),
                "open": candle['open'],
                "high": candle['high'],
                "low": candle['low'],
                "close": candle['close'],
                "volume": candle['volume']
            })
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "data": formatted_data,
            "total": len(formatted_data)
        }
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market-data/batch/current")
async def get_batch_current_prices(
    symbols: List[str],
    current_user: User = Depends(get_current_user)
):
    """
    Get current prices for multiple symbols
    
    - **symbols**: List of trading symbols (max 20)
    """
    if not symbols:
        raise ValidationError("Symbols list cannot be empty")
    
    if len(symbols) > 20:
        raise ValidationError("Maximum 20 symbols per request")
    
    try:
        import asyncio
        
        # Get prices for all symbols concurrently
        tasks = [market_data_service.get_current_price(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Format results
        prices = []
        errors = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append({
                    "symbol": symbols[i],
                    "error": str(result)
                })
            else:
                prices.append({
                    "symbol": result['symbol'],
                    "price": result['price'],
                    "bid": result['bid'],
                    "ask": result['ask'],
                    "volume": result['volume'],
                    "timestamp": result['timestamp'].isoformat(),
                    "ohlc": result['ohlc']
                })
        
        return {
            "prices": prices,
            "errors": errors,
            "total": len(prices),
            "failed": len(errors)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-data/{symbol}/stats")
async def get_symbol_stats(
    symbol: str,
    period_days: int = Query(30, ge=1, le=365, description="Analysis period in days"),
    current_user: User = Depends(get_current_user)
):
    """
    Get statistical analysis for a symbol
    
    - **symbol**: Trading symbol
    - **period_days**: Number of days to analyze (1-365)
    """
    try:
        # Get historical data
        data = await market_data_service.get_historical_data(
            symbol=symbol,
            timeframe='1d',
            days=period_days
        )
        
        if not data:
            raise NotFoundError(f"No data available for {symbol}")
        
        # Calculate statistics
        prices = [candle['close'] for candle in data]
        highs = [candle['high'] for candle in data]
        lows = [candle['low'] for candle in data]
        volumes = [candle['volume'] for candle in data]
        
        # Calculate various metrics
        current_price = prices[-1]
        period_high = max(highs)
        period_low = min(lows)
        avg_price = sum(prices) / len(prices)
        avg_volume = sum(volumes) / len(volumes)
        
        # Calculate price change
        price_change = prices[-1] - prices[0]
        price_change_pct = (price_change / prices[0]) * 100
        
        # Calculate volatility (standard deviation)
        variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
        volatility = variance ** 0.5
        volatility_pct = (volatility / avg_price) * 100
        
        return {
            "symbol": symbol,
            "period_days": period_days,
            "current_price": round(current_price, 5),
            "period_high": round(period_high, 5),
            "period_low": round(period_low, 5),
            "average_price": round(avg_price, 5),
            "average_volume": round(avg_volume, 2),
            "price_change": round(price_change, 5),
            "price_change_pct": round(price_change_pct, 2),
            "volatility": round(volatility, 5),
            "volatility_pct": round(volatility_pct, 2),
            "data_points": len(data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-data/watchlist/summary")
async def get_watchlist_summary(
    symbols: List[str] = Query(["EUR/USD", "GBP/USD", "USD/JPY", "XAU/USD"]),
    current_user: User = Depends(get_current_user)
):
    """
    Get summary data for a watchlist of symbols
    
    - **symbols**: List of symbols to watch (default: major forex pairs)
    """
    if len(symbols) > 10:
        raise ValidationError("Maximum 10 symbols in watchlist")
    
    try:
        import asyncio
        
        # Get current prices for all symbols
        tasks = [market_data_service.get_current_price(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        watchlist = []
        
        for i, result in enumerate(results):
            if not isinstance(result, Exception):
                # Calculate simple indicators
                price = result['price']
                bid = result['bid']
                ask = result['ask']
                spread = ask - bid
                spread_pct = (spread / price) * 100 if price > 0 else 0
                
                watchlist.append({
                    "symbol": result['symbol'],
                    "price": price,
                    "bid": bid,
                    "ask": ask,
                    "spread": round(spread, 5),
                    "spread_pct": round(spread_pct, 2),
                    "change_24h": result['ohlc']['close'] - result['ohlc']['open'],
                    "timestamp": result['timestamp'].isoformat()
                })
        
        return {
            "watchlist": watchlist,
            "total": len(watchlist),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

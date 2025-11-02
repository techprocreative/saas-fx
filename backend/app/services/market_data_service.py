"""
Market Data Service
Implements Phase 2.1 of Production Roadmap
"""
import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class MarketDataProvider:
    """Base class for market data providers"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_current_price(self, symbol: str) -> Dict:
        """Get current price for symbol"""
        raise NotImplementedError
    
    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Get historical OHLCV data"""
        raise NotImplementedError


class CCXTDataProvider(MarketDataProvider):
    """Market data provider using CCXT library"""
    
    def __init__(self):
        super().__init__()
        import ccxt
        # Use a forex/crypto exchange (for demo purposes)
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
        })
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def get_current_price(self, symbol: str) -> Dict:
        """Get current price from exchange"""
        try:
            ticker = await asyncio.to_thread(
                self.exchange.fetch_ticker,
                symbol
            )
            
            return {
                'symbol': symbol,
                'price': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'volume': ticker['volume'],
                'timestamp': datetime.fromtimestamp(ticker['timestamp'] / 1000),
                'ohlc': {
                    'open': ticker['open'],
                    'high': ticker['high'],
                    'low': ticker['low'],
                    'close': ticker['close']
                }
            }
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Get historical OHLCV data"""
        try:
            since = int(start_date.timestamp() * 1000)
            limit = 1000
            
            ohlcv = await asyncio.to_thread(
                self.exchange.fetch_ohlcv,
                symbol,
                timeframe,
                since,
                limit
            )
            
            return [
                {
                    'timestamp': datetime.fromtimestamp(candle[0] / 1000),
                    'open': candle[1],
                    'high': candle[2],
                    'low': candle[3],
                    'close': candle[4],
                    'volume': candle[5]
                }
                for candle in ohlcv
            ]
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            raise


class MockDataProvider(MarketDataProvider):
    """Mock data provider for testing"""
    
    async def get_current_price(self, symbol: str) -> Dict:
        """Get mock current price"""
        import random
        
        base_price = 1.0500 if 'EUR' in symbol else 1800.0
        variation = base_price * 0.001
        
        price = base_price + random.uniform(-variation, variation)
        
        return {
            'symbol': symbol,
            'price': round(price, 5),
            'bid': round(price - 0.0001, 5),
            'ask': round(price + 0.0001, 5),
            'volume': random.randint(1000, 10000),
            'timestamp': datetime.utcnow(),
            'ohlc': {
                'open': round(price - 0.0005, 5),
                'high': round(price + 0.001, 5),
                'low': round(price - 0.001, 5),
                'close': round(price, 5)
            }
        }
    
    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Get mock historical data"""
        import random
        
        data = []
        current = start_date
        base_price = 1.0500 if 'EUR' in symbol else 1800.0
        
        while current < end_date:
            variation = base_price * 0.002
            open_price = base_price + random.uniform(-variation, variation)
            close_price = open_price + random.uniform(-variation, variation)
            high_price = max(open_price, close_price) + random.uniform(0, variation)
            low_price = min(open_price, close_price) - random.uniform(0, variation)
            
            data.append({
                'timestamp': current,
                'open': round(open_price, 5),
                'high': round(high_price, 5),
                'low': round(low_price, 5),
                'close': round(close_price, 5),
                'volume': random.randint(1000, 10000)
            })
            
            current += timedelta(hours=1)  # 1H timeframe
        
        return data


class MarketDataService:
    """
    Main market data service
    Manages data providers and implements failover
    """
    
    def __init__(self):
        # Use mock provider for development
        # Switch to real provider in production
        self.primary_provider = MockDataProvider()
        self.fallback_provider = None  # Can add backup provider
        
        self.cache = {}
        self.cache_ttl = 60  # Cache for 60 seconds
    
    async def get_current_price(self, symbol: str, use_cache: bool = True) -> Dict:
        """
        Get current price with caching
        
        Args:
            symbol: Trading symbol (e.g., 'EUR/USD', 'XAU/USD')
            use_cache: Whether to use cached data
            
        Returns:
            Dict with price data
        """
        cache_key = f"price:{symbol}"
        
        if use_cache and cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if (datetime.utcnow() - cached_time).seconds < self.cache_ttl:
                logger.debug(f"Using cached price for {symbol}")
                return cached_data
        
        try:
            data = await self.primary_provider.get_current_price(symbol)
            self.cache[cache_key] = (data, datetime.utcnow())
            return data
        except Exception as e:
            logger.error(f"Primary provider failed for {symbol}: {e}")
            
            # Try fallback provider
            if self.fallback_provider:
                try:
                    data = await self.fallback_provider.get_current_price(symbol)
                    return data
                except Exception as fallback_error:
                    logger.error(f"Fallback provider also failed: {fallback_error}")
            
            raise Exception(f"Failed to get price for {symbol}")
    
    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str = '1h',
        days: int = 30
    ) -> List[Dict]:
        """
        Get historical data
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            days: Number of days of history
            
        Returns:
            List of OHLCV candles
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        try:
            data = await self.primary_provider.get_historical_data(
                symbol,
                timeframe,
                start_date,
                end_date
            )
            return data
        except Exception as e:
            logger.error(f"Failed to get historical data for {symbol}: {e}")
            raise
    
    async def subscribe_realtime(self, symbol: str, callback):
        """
        Subscribe to real-time price updates
        
        Args:
            symbol: Trading symbol
            callback: Async function to call with updates
        """
        logger.info(f"Starting real-time subscription for {symbol}")
        
        while True:
            try:
                # Get current price every second
                data = await self.get_current_price(symbol, use_cache=False)
                await callback(data)
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                logger.info(f"Real-time subscription cancelled for {symbol}")
                break
            except Exception as e:
                logger.error(f"Error in real-time subscription: {e}")
                await asyncio.sleep(5)  # Wait before retry
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.primary_provider.close()
        if self.fallback_provider:
            await self.fallback_provider.close()


# Global instance
market_data_service = MarketDataService()

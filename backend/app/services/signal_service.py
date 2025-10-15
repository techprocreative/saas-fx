"""
Trading Signal Generation Service
Implements Phase 2.2 of Production Roadmap
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import logging

from app.services.market_data_service import market_data_service

logger = logging.getLogger(__name__)


class SignalType(str, Enum):
    """Trading signal types"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class SignalStrength(str, Enum):
    """Signal strength levels"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class TradingSignal:
    """Trading signal data class"""
    
    def __init__(
        self,
        symbol: str,
        signal_type: SignalType,
        strength: SignalStrength,
        price: float,
        confidence: float,
        indicators: Dict,
        timestamp: Optional[datetime] = None
    ):
        self.symbol = symbol
        self.signal_type = signal_type
        self.strength = strength
        self.price = price
        self.confidence = confidence  # 0.0 to 1.0
        self.indicators = indicators
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """Convert signal to dictionary"""
        return {
            'symbol': self.symbol,
            'signal_type': self.signal_type.value,
            'strength': self.strength.value,
            'price': self.price,
            'confidence': self.confidence,
            'indicators': self.indicators,
            'timestamp': self.timestamp.isoformat()
        }


class TechnicalAnalyzer:
    """Technical analysis for trading signals"""
    
    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> Optional[float]:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> Optional[float]:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(
        prices: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Optional[Dict]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(prices) < slow_period:
            return None
        
        ema_fast = TechnicalAnalyzer.calculate_ema(prices, fast_period)
        ema_slow = TechnicalAnalyzer.calculate_ema(prices, slow_period)
        
        if ema_fast is None or ema_slow is None:
            return None
        
        macd_line = ema_fast - ema_slow
        
        # For signal line, we would need historical MACD values
        # Simplified version here
        signal_line = macd_line * 0.9  # Simplified
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def calculate_bollinger_bands(
        prices: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Optional[Dict]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return None
        
        sma = TechnicalAnalyzer.calculate_sma(prices, period)
        if sma is None:
            return None
        
        # Calculate standard deviation
        recent_prices = prices[-period:]
        variance = sum((p - sma) ** 2 for p in recent_prices) / period
        std = variance ** 0.5
        
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        
        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }


class SignalGenerator:
    """Generate trading signals based on technical analysis"""
    
    def __init__(self):
        self.analyzer = TechnicalAnalyzer()
    
    async def generate_signal(self, symbol: str, timeframe: str = '1h') -> TradingSignal:
        """
        Generate trading signal for a symbol
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe for analysis
            
        Returns:
            TradingSignal object
        """
        try:
            # Get historical data
            historical_data = await market_data_service.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                days=30
            )
            
            if not historical_data or len(historical_data) < 20:
                logger.warning(f"Insufficient data for {symbol}")
                return self._create_hold_signal(symbol, 0.0)
            
            # Extract closing prices
            close_prices = [candle['close'] for candle in historical_data]
            current_price = close_prices[-1]
            
            # Calculate indicators
            indicators = {}
            
            # Moving Averages
            sma_20 = self.analyzer.calculate_sma(close_prices, 20)
            sma_50 = self.analyzer.calculate_sma(close_prices, 50) if len(close_prices) >= 50 else None
            ema_12 = self.analyzer.calculate_ema(close_prices, 12)
            
            indicators['sma_20'] = sma_20
            indicators['sma_50'] = sma_50
            indicators['ema_12'] = ema_12
            
            # RSI
            rsi = self.analyzer.calculate_rsi(close_prices, 14)
            indicators['rsi'] = rsi
            
            # MACD
            macd = self.analyzer.calculate_macd(close_prices)
            indicators['macd'] = macd
            
            # Bollinger Bands
            bb = self.analyzer.calculate_bollinger_bands(close_prices, 20)
            indicators['bollinger_bands'] = bb
            
            # Generate signal based on indicators
            signal = self._analyze_indicators(
                current_price,
                indicators,
                symbol
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            return self._create_hold_signal(symbol, 0.0)
    
    def _analyze_indicators(
        self,
        current_price: float,
        indicators: Dict,
        symbol: str
    ) -> TradingSignal:
        """Analyze indicators and generate signal"""
        
        buy_signals = 0
        sell_signals = 0
        total_weight = 0
        
        # RSI Analysis (Weight: 3)
        rsi = indicators.get('rsi')
        if rsi:
            if rsi < 30:
                buy_signals += 3  # Oversold
            elif rsi > 70:
                sell_signals += 3  # Overbought
            elif 40 <= rsi <= 60:
                pass  # Neutral
            total_weight += 3
        
        # Moving Average Analysis (Weight: 2)
        sma_20 = indicators.get('sma_20')
        if sma_20:
            if current_price > sma_20 * 1.01:  # Price above MA
                buy_signals += 2
            elif current_price < sma_20 * 0.99:  # Price below MA
                sell_signals += 2
            total_weight += 2
        
        # MACD Analysis (Weight: 2)
        macd = indicators.get('macd')
        if macd:
            macd_histogram = macd.get('histogram', 0)
            if macd_histogram > 0:
                buy_signals += 2
            elif macd_histogram < 0:
                sell_signals += 2
            total_weight += 2
        
        # Bollinger Bands Analysis (Weight: 1)
        bb = indicators.get('bollinger_bands')
        if bb:
            if current_price < bb['lower']:
                buy_signals += 1  # Price at lower band
            elif current_price > bb['upper']:
                sell_signals += 1  # Price at upper band
            total_weight += 1
        
        # Calculate confidence
        if total_weight == 0:
            return self._create_hold_signal(symbol, current_price)
        
        buy_confidence = buy_signals / total_weight
        sell_confidence = sell_signals / total_weight
        
        # Determine signal
        if buy_confidence > 0.6:
            signal_type = SignalType.BUY
            strength = SignalStrength.STRONG if buy_confidence > 0.8 else SignalStrength.MODERATE
            confidence = buy_confidence
        elif sell_confidence > 0.6:
            signal_type = SignalType.SELL
            strength = SignalStrength.STRONG if sell_confidence > 0.8 else SignalStrength.MODERATE
            confidence = sell_confidence
        else:
            signal_type = SignalType.HOLD
            strength = SignalStrength.WEAK
            confidence = max(buy_confidence, sell_confidence)
        
        return TradingSignal(
            symbol=symbol,
            signal_type=signal_type,
            strength=strength,
            price=current_price,
            confidence=confidence,
            indicators=indicators
        )
    
    def _create_hold_signal(self, symbol: str, price: float) -> TradingSignal:
        """Create a HOLD signal"""
        return TradingSignal(
            symbol=symbol,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            price=price,
            confidence=0.0,
            indicators={}
        )


class SignalService:
    """
    Main signal generation service
    Manages signal generation and caching
    """
    
    def __init__(self):
        self.generator = SignalGenerator()
        self.signal_cache: Dict[str, TradingSignal] = {}
        self.cache_ttl = 300  # 5 minutes
    
    async def get_signal(self, symbol: str, use_cache: bool = True) -> TradingSignal:
        """
        Get trading signal for symbol
        
        Args:
            symbol: Trading symbol
            use_cache: Whether to use cached signal
            
        Returns:
            TradingSignal object
        """
        cache_key = f"signal:{symbol}"
        
        if use_cache and cache_key in self.signal_cache:
            cached_signal = self.signal_cache[cache_key]
            age = (datetime.utcnow() - cached_signal.timestamp).seconds
            
            if age < self.cache_ttl:
                logger.debug(f"Using cached signal for {symbol}")
                return cached_signal
        
        # Generate new signal
        signal = await self.generator.generate_signal(symbol)
        self.signal_cache[cache_key] = signal
        
        return signal
    
    async def get_signals_batch(self, symbols: List[str]) -> Dict[str, TradingSignal]:
        """Get signals for multiple symbols"""
        signals = {}
        
        # Generate signals concurrently
        tasks = [self.get_signal(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.error(f"Error generating signal for {symbol}: {result}")
                signals[symbol] = self.generator._create_hold_signal(symbol, 0.0)
            else:
                signals[symbol] = result
        
        return signals
    
    async def monitor_signals(self, symbols: List[str], callback):
        """
        Monitor signals for multiple symbols
        
        Args:
            symbols: List of symbols to monitor
            callback: Async function to call with signal updates
        """
        logger.info(f"Starting signal monitoring for {len(symbols)} symbols")
        
        while True:
            try:
                signals = await self.get_signals_batch(symbols)
                
                # Filter for actionable signals (BUY/SELL)
                actionable = {
                    symbol: signal
                    for symbol, signal in signals.items()
                    if signal.signal_type != SignalType.HOLD
                }
                
                if actionable:
                    await callback(actionable)
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                logger.info("Signal monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error in signal monitoring: {e}")
                await asyncio.sleep(30)  # Wait before retry


# Global instance
signal_service = SignalService()

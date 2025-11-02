"""
Trading Signal Generation Service
Implements Phase 2.2 of Production Roadmap
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import logging

from app.services.market_data_service import market_data_service

logger = logging.getLogger(__name__)


class SignalType(str, Enum):
    """Signal types"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class SignalStrength(str, Enum):
    """Signal strength levels"""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


class TradingSignal:
    """Trading signal data structure"""
    
    def __init__(
        self,
        symbol: str,
        signal_type: SignalType,
        strength: SignalStrength,
        confidence: float,
        entry_price: float,
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
        indicators: Optional[Dict] = None,
        timestamp: Optional[datetime] = None
    ):
        self.symbol = symbol
        self.signal_type = signal_type
        self.strength = strength
        self.confidence = confidence
        self.entry_price = entry_price
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.indicators = indicators or {}
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """Convert signal to dictionary"""
        return {
            'symbol': self.symbol,
            'signal_type': self.signal_type.value,
            'strength': self.strength.value,
            'confidence': self.confidence,
            'entry_price': self.entry_price,
            'take_profit': self.take_profit,
            'stop_loss': self.stop_loss,
            'indicators': self.indicators,
            'timestamp': self.timestamp.isoformat()
        }


class TechnicalIndicators:
    """Calculate technical indicators for signal generation"""
    
    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> float:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return 0.0
        return sum(prices[-period:]) / period
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return 0.0
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0  # Neutral
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(prices: List[float]) -> Dict[str, float]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(prices) < 26:
            return {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0}
        
        ema_12 = TechnicalIndicators.calculate_ema(prices, 12)
        ema_26 = TechnicalIndicators.calculate_ema(prices, 26)
        macd_line = ema_12 - ema_26
        
        # Signal line (9-period EMA of MACD)
        signal_line = macd_line * 0.9  # Simplified
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }


class SignalGenerator:
    """Generate trading signals based on technical analysis"""
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
    
    async def generate_signal(self, symbol: str) -> Optional[TradingSignal]:
        """
        Generate trading signal for a symbol
        
        Args:
            symbol: Trading symbol (e.g., 'EUR/USD')
            
        Returns:
            TradingSignal or None if no clear signal
        """
        try:
            # Get historical data
            historical_data = await market_data_service.get_historical_data(
                symbol=symbol,
                timeframe='1h',
                days=7
            )
            
            if len(historical_data) < 50:
                logger.warning(f"Insufficient data for {symbol}")
                return None
            
            # Extract closing prices
            prices = [candle['close'] for candle in historical_data]
            current_price = prices[-1]
            
            # Calculate indicators
            sma_20 = self.indicators.calculate_sma(prices, 20)
            sma_50 = self.indicators.calculate_sma(prices, 50)
            ema_12 = self.indicators.calculate_ema(prices, 12)
            rsi = self.indicators.calculate_rsi(prices)
            macd = self.indicators.calculate_macd(prices)
            
            # Signal generation logic
            signal_type = SignalType.HOLD
            strength = SignalStrength.WEAK
            confidence = 0.5
            
            # Bullish signals
            bullish_signals = 0
            if current_price > sma_20:
                bullish_signals += 1
            if sma_20 > sma_50:
                bullish_signals += 1
            if rsi < 30:  # Oversold
                bullish_signals += 2
            if macd['histogram'] > 0:
                bullish_signals += 1
            
            # Bearish signals
            bearish_signals = 0
            if current_price < sma_20:
                bearish_signals += 1
            if sma_20 < sma_50:
                bearish_signals += 1
            if rsi > 70:  # Overbought
                bearish_signals += 2
            if macd['histogram'] < 0:
                bearish_signals += 1
            
            # Determine signal
            if bullish_signals >= 3:
                signal_type = SignalType.BUY
                strength = SignalStrength.STRONG if bullish_signals >= 4 else SignalStrength.MODERATE
                confidence = min(0.9, 0.5 + (bullish_signals * 0.1))
            elif bearish_signals >= 3:
                signal_type = SignalType.SELL
                strength = SignalStrength.STRONG if bearish_signals >= 4 else SignalStrength.MODERATE
                confidence = min(0.9, 0.5 + (bearish_signals * 0.1))
            
            # Calculate take profit and stop loss
            take_profit = None
            stop_loss = None
            
            if signal_type == SignalType.BUY:
                take_profit = current_price * 1.02  # 2% profit
                stop_loss = current_price * 0.99    # 1% loss
            elif signal_type == SignalType.SELL:
                take_profit = current_price * 0.98  # 2% profit
                stop_loss = current_price * 1.01    # 1% loss
            
            # Create signal
            signal = TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                strength=strength,
                confidence=confidence,
                entry_price=current_price,
                take_profit=take_profit,
                stop_loss=stop_loss,
                indicators={
                    'sma_20': round(sma_20, 5),
                    'sma_50': round(sma_50, 5),
                    'ema_12': round(ema_12, 5),
                    'rsi': round(rsi, 2),
                    'macd': {
                        'macd': round(macd['macd'], 5),
                        'signal': round(macd['signal'], 5),
                        'histogram': round(macd['histogram'], 5)
                    },
                    'bullish_signals': bullish_signals,
                    'bearish_signals': bearish_signals
                }
            )
            
            logger.info(
                f"Generated {signal_type.value} signal for {symbol}",
                extra={
                    'symbol': symbol,
                    'signal': signal_type.value,
                    'confidence': confidence,
                    'strength': strength.value
                }
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            return None
    
    async def generate_signals_batch(self, symbols: List[str]) -> List[TradingSignal]:
        """
        Generate signals for multiple symbols
        
        Args:
            symbols: List of trading symbols
            
        Returns:
            List of trading signals
        """
        tasks = [self.generate_signal(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        signals = []
        for result in results:
            if isinstance(result, TradingSignal):
                signals.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Error in batch signal generation: {result}")
        
        return signals


class SignalService:
    """
    Main signal service
    Manages signal generation and validation
    """
    
    def __init__(self):
        self.generator = SignalGenerator()
        self.active_signals: Dict[str, TradingSignal] = {}
        self.signal_history: List[TradingSignal] = []
    
    async def get_signal(self, symbol: str, force_regenerate: bool = False) -> Optional[TradingSignal]:
        """
        Get trading signal for symbol
        
        Args:
            symbol: Trading symbol
            force_regenerate: Force signal regeneration
            
        Returns:
            TradingSignal or None
        """
        # Check if we have a recent signal
        if not force_regenerate and symbol in self.active_signals:
            signal = self.active_signals[symbol]
            age = (datetime.utcnow() - signal.timestamp).seconds
            
            if age < 3600:  # Signal valid for 1 hour
                logger.debug(f"Using cached signal for {symbol}")
                return signal
        
        # Generate new signal
        signal = await self.generator.generate_signal(symbol)
        
        if signal:
            self.active_signals[symbol] = signal
            self.signal_history.append(signal)
            
            # Keep only last 1000 signals in history
            if len(self.signal_history) > 1000:
                self.signal_history = self.signal_history[-1000:]
        
        return signal
    
    async def get_signals_batch(self, symbols: List[str]) -> Dict[str, TradingSignal]:
        """Get signals for multiple symbols"""
        signals = await self.generator.generate_signals_batch(symbols)
        
        result = {}
        for signal in signals:
            result[signal.symbol] = signal
            self.active_signals[signal.symbol] = signal
            self.signal_history.append(signal)
        
        return result
    
    def get_signal_history(self, symbol: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get signal history"""
        history = self.signal_history
        
        if symbol:
            history = [s for s in history if s.symbol == symbol]
        
        return [s.to_dict() for s in history[-limit:]]
    
    def validate_signal(self, signal: TradingSignal) -> bool:
        """
        Validate a trading signal
        
        Args:
            signal: Trading signal to validate
            
        Returns:
            True if signal is valid
        """
        # Check confidence threshold
        if signal.confidence < 0.6:
            logger.warning(f"Signal confidence too low: {signal.confidence}")
            return False
        
        # Check if signal is too old
        age = (datetime.utcnow() - signal.timestamp).seconds
        if age > 3600:  # 1 hour
            logger.warning(f"Signal too old: {age}s")
            return False
        
        # Check if take profit and stop loss are set
        if signal.signal_type != SignalType.HOLD:
            if not signal.take_profit or not signal.stop_loss:
                logger.warning("Missing take profit or stop loss")
                return False
        
        return True


# Global instance
signal_service = SignalService()

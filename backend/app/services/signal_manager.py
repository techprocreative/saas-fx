import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import TradingAccount, AIStrategy, Trade, OrderType, TradeStatus
from app.services.websocket_transmitter import signal_transmitter

logger = logging.getLogger(__name__)

class PlatformSignalManager:
    """Platform-side signal management and processing"""
    
    def __init__(self):
        self.signal_transmitter = signal_transmitter
        self.freqtrade_engine = None  # Will be initialized later
        self.active_strategies: Dict[str, Dict] = {}  # strategy_id: strategy_info
        self.market_data_cache: Dict[str, Dict] = {}  # symbol: market_data
        
    def set_freqtrade_engine(self, freqtrade_engine):
        """Set Freqtrade engine instance"""
        self.freqtrade_engine = freqtrade_engine
    
    async def process_market_data(self, market_data: dict):
        """Process real-time market data and generate signals"""
        try:
            # Cache market data
            symbol = market_data.get('symbol')
            if symbol:
                self.market_data_cache[symbol] = {
                    'data': market_data,
                    'timestamp': datetime.utcnow()
                }
            
            # Get all active users with connected accounts
            if not self.freqtrade_engine:
                logger.warning("Freqtrade engine not initialized")
                return
            
            active_users = await self.get_active_users()
            
            for user_id in active_users:
                try:
                    await self._process_user_signals(user_id, market_data)
                except Exception as e:
                    logger.error(f"Error processing signals for user {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in process_market_data: {e}")
    
    async def get_active_users(self) -> List[str]:
        """Get list of users with connected accounts and active strategies"""
        from app.core.database import get_db
        
        try:
            db = next(get_db())
            
            # Get users with online trading accounts
            online_accounts = db.query(TradingAccount).filter(
                TradingAccount.connection_status == "online"
            ).all()
            
            user_ids = list(set([account.user_id for account in online_accounts]))
            
            # Filter users with active strategies
            active_users = []
            for user_id in user_ids:
                active_strategies = db.query(AIStrategy).filter(
                    AIStrategy.user_id == user_id,
                    AIStrategy.status == "active"
                ).count()
                
                if active_strategies > 0:
                    active_users.append(user_id)
            
            db.close()
            return active_users
            
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []
    
    async def _process_user_signals(self, user_id: str, market_data: dict):
        """Process trading signals for specific user"""
        from app.core.database import get_db
        
        try:
            db = next(get_db())
            
            # Get user strategies
            strategies = db.query(AIStrategy).filter(
                AIStrategy.user_id == user_id,
                AIStrategy.status == "active"
            ).all()
            
            for strategy in strategies:
                try:
                    # Check if strategy should trade this symbol/timeframe
                    if not self._should_trade_symbol(strategy, market_data):
                        continue
                    
                    # Generate signal using Freqtrade + AI strategy
                    signal = await self._generate_signal(strategy, market_data)
                    
                    if signal and await self._validate_signal(signal):
                        # Log signal for tracking
                        signal_id = await self._log_signal(user_id, strategy.id, signal)
                        signal['id'] = signal_id
                        
                        # Send signal to user's MT5
                        success = await self.signal_transmitter.send_signal_to_user(
                            user_id, signal
                        )
                        
                        if success:
                            logger.info(f"Signal {signal_id} sent to user {user_id} for {signal['symbol']}")
                        else:
                            logger.warning(f"Failed to send signal {signal_id} to user {user_id}")
                            
                except Exception as e:
                    logger.error(f"Error processing strategy {strategy.id}: {e}")
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error processing user signals: {e}")
    
    async def _generate_signal(self, strategy: AIStrategy, market_data: dict) -> Optional[dict]:
        """Generate signal using Freqtrade with AI strategy configuration"""
        try:
            if not self.freqtrade_engine:
                logger.error("Freqtrade engine not available")
                return None
            
            # Parse strategy configuration
            strategy_config = json.loads(strategy.strategy_config) if strategy.strategy_config else {}
            
            # Generate signal using modified Freqtrade
            signal = await self.freqtrade_engine.generate_signal(
                strategy_id=strategy.id,
                strategy_config=strategy_config,
                market_data=market_data
            )
            
            if signal:
                # Add additional signal metadata
                signal.update({
                    'strategy_id': str(strategy.id),
                    'strategy_name': strategy.name,
                    'ai_model': strategy.llm_model,
                    'generated_at': datetime.utcnow().isoformat(),
                    'user_id': str(strategy.user_id)
                })
            
            return signal
            
        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return None
    
    def _should_trade_symbol(self, strategy: AIStrategy, market_data: dict) -> bool:
        """Check if strategy should trade the current symbol"""
        try:
            symbol = market_data.get('symbol')
            if not symbol:
                return False
            
            # Parse strategy config to get allowed symbols
            strategy_config = json.loads(strategy.strategy_config) if strategy.strategy_config else {}
            preferred_pairs = strategy_config.get('pairs', [])
            
            # If no preferred pairs specified, allow all
            if not preferred_pairs:
                return True
            
            # Check if current symbol is in preferred pairs
            return symbol in preferred_pairs
            
        except Exception as e:
            logger.error(f"Error checking symbol permission: {e}")
            return True  # Default to allow if error
    
    async def _validate_signal(self, signal: dict) -> bool:
        """Validate trading signal before sending"""
        try:
            required_fields = ['symbol', 'type', 'volume', 'price']
            
            for field in required_fields:
                if field not in signal:
                    logger.warning(f"Signal missing required field: {field}")
                    return False
            
            # Validate signal values
            if signal['type'] not in ['BUY', 'SELL']:
                logger.warning(f"Invalid signal type: {signal['type']}")
                return False
            
            if float(signal['volume']) <= 0:
                logger.warning(f"Invalid volume: {signal['volume']}")
                return False
            
            if float(signal['price']) <= 0:
                logger.warning(f"Invalid price: {signal['price']}")
                return False
            
            # Additional business rules validation
            if float(signal['volume']) > 10.0:  # Max volume check
                logger.warning(f"Volume too large: {signal['volume']}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating signal: {e}")
            return False
    
    async def _log_signal(self, user_id: str, strategy_id: str, signal: dict) -> str:
        """Log signal for tracking and analysis"""
        try:
            from app.core.database import get_db
            from app.models import Trade, OrderType, TradeStatus
            import uuid
            
            db = next(get_db())
            
            # Create trade record for the signal
            trade = Trade(
                id=uuid.uuid4(),
                account_id=None,  # Will be updated when account processes signal
                strategy_id=strategy_id,
                symbol=signal['symbol'],
                type=OrderType.BUY if signal['type'] == 'BUY' else OrderType.SELL,
                volume=float(signal['volume']),
                open_price=float(signal['price']),
                stop_loss=float(signal.get('stop_loss', 0)),
                take_profit=float(signal.get('take_profit', 0)),
                status=TradeStatus.OPEN,
                opened_at=datetime.utcnow()
            )
            
            db.add(trade)
            db.commit()
            
            signal_id = str(trade.id)
            db.close()
            
            logger.info(f"Signal logged with ID: {signal_id}")
            return signal_id
            
        except Exception as e:
            logger.error(f"Error logging signal: {e}")
            # Generate a temporary ID if logging fails
            import uuid
            return str(uuid.uuid4())
    
    async def handle_trade_result(self, user_id: str, trade_data: dict):
        """Handle trade execution result from user's MT5"""
        try:
            from app.core.database import get_db
            from app.models import Trade, Commission, CommissionStatus
            
            db = next(get_db())
            
            # Update database with actual trade data
            signal_id = trade_data.get('signal_id')
            if signal_id:
                trade = db.query(Trade).filter(Trade.id == signal_id).first()
                
                if trade:
                    # Update trade information
                    trade.status = TradeStatus.CLOSED if trade_data.get('status') == 'executed' else TradeStatus.OPEN
                    trade.mt5_order_id = trade_data.get('order_id')
                    trade.mt5_position_id = trade_data.get('position_id')
                    trade.close_price = trade_data.get('execution_price')
                    trade.profit_loss = trade_data.get('profit', 0.0)
                    trade.closed_at = datetime.utcnow()
                    
                    # Calculate commission for profitable trade
                    if trade.profit_loss > 0:
                        from app.services.commission_service import CommissionCalculator
                        calculator = CommissionCalculator()
                        commission_data = calculator.calculate_commission({
                            'id': str(trade.id),
                            'volume': float(trade.volume),
                            'profit_loss': float(trade.profit_loss)
                        })
                        
                        commission = Commission(
                            trade_id=trade.id,
                            user_id=user_id,
                            amount=commission_data['total'],
                            volume_commission=commission_data['volume_commission'],
                            profit_commission=commission_data['profit_commission'],
                            status='pending'
                        )
                        db.add(commission)
                    
                    db.commit()
                    logger.info(f"Updated trade {signal_id} with execution result")
                else:
                    logger.warning(f"Trade not found for signal_id: {signal_id}")
            
            # Update account balance if provided
            account_data = trade_data.get('account')
            if account_data:
                await self._sync_account_balance(user_id, account_data)
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error handling trade result: {e}")
    
    async def _sync_account_balance(self, user_id: str, account_data: dict):
        """Sync account balance from client"""
        try:
            from app.core.database import get_db
            from app.models import TradingAccount
            
            db = next(get_db())
            
            account = db.query(TradingAccount).filter(
                TradingAccount.user_id == user_id,
                TradingAccount.mt5_login == account_data.get('login')
            ).first()
            
            if account:
                account.balance = account_data.get('balance', account.balance)
                account.last_ping = datetime.utcnow()
                db.commit()
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error syncing account balance: {e}")
    
    async def log_signal(self, user_id: str, strategy_id: str, signal: dict):
        """Log signal for tracking (legacy method)"""
        await self._log_signal(user_id, strategy_id, signal)
    
    def validate_signal(self, signal: dict) -> bool:
        """Validate signal (legacy method)"""
        return asyncio.run(self._validate_signal(signal))

class ModifiedFreqtrade:
    """Custom Freqtrade adapter for signal generation"""
    
    def __init__(self):
        self.strategies = {}
        self.market_data = {}
    
    async def generate_signal(
        self, 
        strategy_id: str, 
        strategy_config: dict, 
        market_data: dict
    ) -> Optional[dict]:
        """Generate trading signal based on strategy config and market data"""
        try:
            # This is a simplified version - in production, this would integrate
            # with actual Freqtrade API or a custom implementation
            
            symbol = market_data.get('symbol')
            
            # Get technical indicators from market data
            indicators = self._calculate_indicators(market_data, strategy_config)
            
            # Apply strategy rules
            signal = self._apply_strategy_rules(indicators, strategy_config)
            
            if signal:
                return {
                    'symbol': symbol,
                    'type': signal['type'],
                    'volume': signal['volume'],
                    'price': market_data.get('price', 0),
                    'stop_loss': signal.get('stop_loss'),
                    'take_profit': signal.get('take_profit'),
                    'confidence': signal.get('confidence', 0.7),
                    'reason': signal.get('reason', 'AI signal generated'),
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return None
    
    def _calculate_indicators(self, market_data: dict, strategy_config: dict) -> dict:
        """Calculate technical indicators"""
        # Simplified indicator calculation
        indicators = {
            'current_price': market_data.get('price', 0),
            'volume': market_data.get('volume', 0),
            'timestamp': market_data.get('timestamp', datetime.utcnow().isoformat())
        }
        
        # Add basic indicators if data is available
        if 'ohlc' in market_data:
            ohlc = market_data['ohlc']
            indicators.update({
                'open': ohlc.get('open', 0),
                'high': ohlc.get('high', 0),
                'low': ohlc.get('low', 0),
                'close': ohlc.get('close', 0)
            })
            
            # Simple moving averages
            closes = [ohlc.get('close', 0)] * 20  # Simplified
            if closes:
                indicators['sma_20'] = sum(closes) / len(closes)
                indicators['sma_50'] = sum(closes) / len(closes)  # Simplified
            
            # RSI (simplified)
            indicators['rsi'] = 50  # Neutral
        
        return indicators
    
    def _apply_strategy_rules(self, indicators: dict, strategy_config: dict) -> Optional[dict]:
        """Apply trading strategy rules to indicators"""
        try:
            # Simplified strategy logic
            entry_rules = strategy_config.get('entry_rules', {})
            risk_management = strategy_config.get('risk_management', {})
            
            # Check for buy signals
            buy_conditions = entry_rules.get('buy_conditions', [])
            sell_conditions = entry_rules.get('sell_conditions', [])
            
            signal = None
            
            # Simple trend following logic
            if 'sma_20' in indicators and 'sma_50' in indicators:
                sma_20 = indicators['sma_20']
                sma_50 = indicators['sma_50']
                price = indicators['current_price']
                
                if price > sma_20 > sma_50 and indicators.get('rsi', 50) < 70:
                    signal = {
                        'type': 'BUY',
                        'stop_loss': price * 0.985,  # 1.5% below
                        'take_profit': price * 1.03,  # 3% above
                        'volume': risk_management.get('max_risk_per_trade', 2.0) / 100,
                        'confidence': 0.7,
                        'reason': 'Price above SMAs with RSI confirmation'
                    }
                elif price < sma_20 < sma_50 and indicators.get('rsi', 50) > 30:
                    signal = {
                        'type': 'SELL',
                        'stop_loss': price * 1.015,  # 1.5% above
                        'take_profit': price * 0.97,  # 3% below
                        'volume': risk_management.get('max_risk_per_trade', 2.0) / 100,
                        'confidence': 0.7,
                        'reason': 'Price below SMAs with RSI confirmation'
                    }
            
            return signal
            
        except Exception as e:
            logger.error(f"Error applying strategy rules: {e}")
            return None

# Global instances
platform_signal_manager = PlatformSignalManager()
modified_freqtrade = ModifiedFreqtrade()

# Initialize the connection
platform_signal_manager.set_freqtrade_engine(modified_freqtrade)

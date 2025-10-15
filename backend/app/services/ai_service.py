import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
import aiohttp
from app.core.config import settings

logger = logging.getLogger(__name__)

class OpenRouterClient:
    """Client for OpenRouter API to access various LLM models"""
    
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://forex-ai-platform.com",
            "X-Title": "Forex AI Trading Platform"
        }
    
    async def complete(self, model: str, prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """Make completion request to OpenRouter API"""
        if not self.api_key:
            raise ValueError("OpenRouter API key not configured")
        
        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content']
                    else:
                        error_text = await response.text()
                        logger.error(f"OpenRouter API error: {response.status} - {error_text}")
                        raise Exception(f"OpenRouter API error: {response.status}")
        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {e}")
            raise

class AIStrategyGenerator:
    """Service for generating AI trading strategies using LLM"""
    
    def __init__(self):
        self.openrouter_client = OpenRouterClient()
        self.strategy_templates = StrategyTemplates()
    
    async def generate_strategy(
        self,
        user_preferences: dict,
        market_conditions: dict,
        selected_model: str = settings.DEFAULT_AI_MODEL
    ) -> dict:
        """
        Generate trading strategy based on:
        - User risk profile
        - Market analysis
        - Historical performance
        """
        try:
            # Build comprehensive prompt for strategy generation
            prompt = self._build_strategy_prompt(user_preferences, market_conditions)
            
            logger.info(f"Generating strategy using model: {selected_model}")
            
            # Call OpenRouter API with selected model
            response = await self.openrouter_client.complete(
                model=selected_model,
                prompt=prompt,
                temperature=0.7
            )
            
            logger.info(f"AI strategy response received: {len(response)} characters")
            
            # Parse and validate strategy
            strategy = self._parse_strategy_response(response)
            validated_strategy = self._validate_strategy(strategy, user_preferences)
            
            # Convert to Freqtrade format
            freqtrade_config = self._convert_to_freqtrade(validated_strategy)
            
            logger.info("AI strategy generated and validated successfully")
            
            return {
                'raw_response': response,
                'strategy': validated_strategy,
                'freqtrade_config': freqtrade_config,
                'model_used': selected_model,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating AI strategy: {e}")
            raise
    
    def _build_strategy_prompt(self, user_preferences: dict, market_conditions: dict) -> str:
        """Build comprehensive prompt for strategy generation"""
        
        prompt = f"""
You are an expert forex trading strategist with deep knowledge of technical analysis, risk management, and algorithmic trading. 
Generate a comprehensive trading strategy for a forex trader based on the following requirements:

USER PREFERENCES:
- Risk Level: {user_preferences.get('risk_level', 'medium')}
- Trading Style: {user_preferences.get('trading_style', 'swing')}
- Preferred Timeframes: {', '.join(user_preferences.get('timeframes', ['H1', 'H4']))}
- Maximum Risk per Trade: {user_preferences.get('max_risk_percent', 2.0)}%
- Currency Pairs: {', '.join(user_preferences.get('preferred_pairs', ['EUR/USD', 'GBP/USD']))}
- Trading Sessions: {', '.join(user_preferences.get('sessions', ['London', 'New York']))}

CURRENT MARKET CONDITIONS:
- Overall Trend: {market_conditions.get('trend', 'neutral')}
- Volatility Level: {market_conditions.get('volatility', 'medium')}
- Key Economic Events: {market_conditions.get('economic_events', 'None')}
- Market Sentiment: {market_conditions.get('sentiment', 'neutral')}

STRATEGY REQUIREMENTS:

1. Generate a detailed trading strategy with the following components:
   - Entry conditions (specific technical indicators and criteria)
   - Exit conditions (take profit, stop loss rules)
   - Risk management rules
   - Position sizing strategy
   - Time filters and session restrictions

2. Include specific technical indicators with their parameters:
   - Moving averages (periods, types)
   - Oscillators (RSI, Stochastic, MACD parameters)
   - Support/Resistance identification
   - Volume analysis if applicable

3. Provide clear rules for:
   - When to enter trades (AND/OR conditions)
   - When to exit (profit targets and stop losses)
   - Trade management (trailing stops, partial exits)
   - Risk management (maximum drawdown, consecutive losses)

4. Output the strategy in JSON format with this structure:
{{
   "strategy_name": "Descriptive strategy name",
   "strategy_type": "trend_following/mean_reversion/breakthrough/scalping",
   "timeframes": ["H1", "H4"],
   "pairs": ["EURUSD", "GBPUSD"],
   "indicators": {{
       "ema_fast": {{"period": 20, "type": "exponential"}},
       "ema_slow": {{"period": 50, "type": "exponential"}},
       "rsi": {{"period": 14, "overbought": 70, "oversold": 30}},
       "macd": {{"fast": 12, "slow": 26, "signal": 9}}
   }},
   "entry_rules": {{
       "buy_conditions": [
           {{
               "indicator": "ema_cross",
               "condition": "ema_fast > ema_slow",
               "additional_filter": "rsi < 70"
           }}
       ],
       "sell_conditions": [
           {{
               "indicator": "ema_cross",
               "condition": "ema_fast < ema_slow",
               "additional_filter": "rsi > 30"
           }}
       ]
   }},
   "exit_rules": {{
       "take_profit": {{
           "type": "ratio",
           "value": 2.0,
           "description": "2:1 risk reward ratio"
       }},
       "stop_loss": {{
           "type": "percentage",
           "value": 1.5,
           "description": "1.5% of account balance"
       }},
       "trailing_stop": {{
           "enabled": true,
           "activation": 1.0,
           "distance": 0.5
       }}
   }},
   "risk_management": {{
       "max_risk_per_trade": 2.0,
       "max_open_positions": 3,
       "max_daily_loss": 5.0,
       "correlation_limit": 0.7
   }},
   "time_filters": {{
       "trading_sessions": ["London", "New York"],
       "avoid_news": true,
       "weekend_trading": false
   }},
   "expected_performance": {{
       "win_rate": 65,
       "profit_factor": 1.8,
       "max_drawdown": 15,
       "sharpe_ratio": 1.2
   }}
}}

Please generate a strategy that is:
- Realistic and implementable
- Consistent with the user's risk tolerance
- Suitable for current market conditions
- Detailed enough for actual implementation

Focus on creating a robust strategy with clear, quantifiable rules that can be directly implemented in a trading system.
"""
        
        return prompt
    
    def _parse_strategy_response(self, response: str) -> dict:
        """Parse AI response to extract strategy JSON"""
        try:
            # Try to extract JSON from the response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                strategy = json.loads(json_str)
                return strategy
            else:
                # If no JSON found, create a basic strategy structure
                logger.warning("No JSON found in AI response, creating basic structure")
                return {
                    "strategy_name": "AI Generated Strategy",
                    "raw_response": response,
                    "status": "manual_review_required"
                }
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing AI strategy response: {e}")
            return {
                "strategy_name": "AI Generated Strategy",
                "raw_response": response,
                "status": "parse_error",
                "error": str(e)
            }
    
    def _validate_strategy(self, strategy: dict, user_preferences: dict) -> dict:
        """Validate and sanitize generated strategy"""
        try:
            # Basic validation
            if not strategy.get('strategy_name'):
                strategy['strategy_name'] = "AI Generated Strategy"
            
            # Validate risk levels
            max_risk = strategy.get('risk_management', {}).get('max_risk_per_trade', 2.0)
            user_max_risk = user_preferences.get('max_risk_percent', 2.0)
            
            if max_risk > user_max_risk:
                strategy['risk_management']['max_risk_per_trade'] = user_max_risk
                logger.info(f"Adjusted max risk per trade to user limit: {user_max_risk}%")
            
            # Ensure required sections exist
            required_sections = ['indicators', 'entry_rules', 'exit_rules', 'risk_management']
            for section in required_sections:
                if section not in strategy:
                    strategy[section] = {}
            
            strategy['validated_at'] = datetime.utcnow().isoformat()
            strategy['status'] = 'validated'
            
            return strategy
            
        except Exception as e:
            logger.error(f"Error validating strategy: {e}")
            strategy['status'] = 'validation_error'
            strategy['validation_error'] = str(e)
            return strategy
    
    def _convert_to_freqtrade(self, strategy: dict) -> dict:
        """Convert AI strategy to Freqtrade configuration format"""
        freqtrade_config = {
            "strategy_name": strategy.get('strategy_name', 'ai_strategy'),
            "strategy_type": strategy.get('strategy_type', 'custom'),
            "timeframe": strategy.get('timeframes', ['H1'])[0],  # Use primary timeframe
            
            # Technical indicators configuration
            "technical_indicators": strategy.get('indicators', {}),
            
            # Trading rules
            "minimal_roi": self._convert_roi_rules(strategy.get('exit_rules', {})),
            "stoploss": self._convert_stoploss_rules(strategy.get('exit_rules', {})),
            "trailing_stop": self._convert_trailing_stop_rules(strategy.get('exit_rules', {})),
            
            # Risk management
            "max_open_trades": strategy.get('risk_management', {}).get('max_open_positions', 3),
            "stake_amount": strategy.get('risk_management', {}).get('max_risk_per_trade', 2.0) / 100,
            
            # Filters
            "timeframe_detail": strategy.get('timeframes', ['H1']),
            "process_only_new_candles": True,
            
            # Protection
            "protections": self._generate_protection_rules(strategy.get('risk_management', {})),
            
            # Metadata
            "generated_at": datetime.utcnow().isoformat(),
            "ai_generated": True,
            "original_ai_strategy": strategy
        }
        
        return freqtrade_config
    
    def _convert_roi_rules(self, exit_rules: dict) -> dict:
        """Convert exit rules to Freqtrade minimal_roi format"""
        take_profit = exit_rules.get('take_profit', {})
        
        if take_profit.get('type') == 'ratio':
            # Convert risk:reward ratio to ROI timeline
            ratio = take_profit.get('value', 2.0)
            return {
                "0": min(ratio * 100, 100),  # ROI % based on ratio
            }
        elif take_profit.get('type') == 'percentage':
            percentage = take_profit.get('value', 2.0)
            return {
                "0": percentage,
            }
        else:
            # Default ROI
            return {"0": 10}  # 10% ROI
    
    def _convert_stoploss_rules(self, exit_rules: dict) -> float:
        """Convert stop loss rules to Freqtrade format"""
        stop_loss = exit_rules.get('stop_loss', {})
        
        if stop_loss.get('type') == 'percentage':
            return -abs(stop_loss.get('value', 1.5)) / 100
        else:
            return -0.015  # Default -1.5%
    
    def _convert_trailing_stop_rules(self, exit_rules: dict) -> dict:
        """Convert trailing stop rules to Freqtrade format"""
        trailing = exit_rules.get('trailing_stop', {})
        
        if trailing.get('enabled'):
            return {
                "trailing_stop": True,
                "trailing_stop_positive": trailing.get('activation', 1.0) / 100,
                "trailing_stop_positive_offset": trailing.get('distance', 0.5) / 100 + 0.001,
            }
        else:
            return {"trailing_stop": False}
    
    def _generate_protection_rules(self, risk_management: dict) -> list:
        """Generate Freqtrade protection rules"""
        protections = []
        
        # Stop trading after certain daily loss
        max_daily_loss = risk_management.get('max_daily_loss', 5.0)
        protections.append({
            "method": "StoplossGuard",
            "lookback_period_candles": 1440,  # 1 day in H1 timeframe
            "trade_limit": 20,
            "stop_duration_candles": 1440,
            "only_per_pair": False
        })
        
        return protections

class TradingSupervision:
    """Service for AI-based trading supervision"""
    
    def __init__(self):
        self.openrouter_client = OpenRouterClient()
        self.risk_manager = None  # Would be injected
    
    async def supervise_trading(
        self,
        current_positions: list,
        market_data: dict,
        strategy_performance: dict
    ) -> dict:
        """
        AI supervises ongoing trading:
        - Monitor risk levels
        - Suggest adjustments
        - Alert on anomalies
        """
        try:
            prompt = self._build_supervision_prompt(
                current_positions, market_data, strategy_performance
            )
            
            response = await self.openrouter_client.complete(
                model=settings.DEFAULT_AI_MODEL,
                prompt=prompt
            )
            
            analysis = self._parse_supervision_response(response)
            
            recommendations = {
                'continue': analysis.get('confidence', 0) > 0.7,
                'adjustments': analysis.get('suggested_changes', []),
                'risk_alerts': analysis.get('risk_warnings', []),
                'stop_trading': analysis.get('critical_issues', []),
                'supervision_timestamp': datetime.utcnow().isoformat(),
                'ai_analysis': analysis
            }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error in trading supervision: {e}")
            return {
                'continue': False,
                'error': str(e),
                'supervision_timestamp': datetime.utcnow().isoformat()
            }
    
    def _build_supervision_prompt(self, positions: list, market: dict, performance: dict) -> str:
        """Build prompt for trading supervision"""
        
        prompt = f"""
You are an expert risk manager supervising automated forex trading. Analyze the current trading situation and provide supervision recommendations.

CURRENT POSITIONS:
{json.dumps(positions, indent=2)}

MARKET CONDITIONS:
{json.dumps(market, indent=2)}

STRATEGY PERFORMANCE:
{json.dumps(performance, indent=2)}

Please analyze the situation and provide:
1. Risk assessment (scale 0-10 confidence)
2. Any concerning patterns or anomalies
3. Recommended adjustment actions
4. Whether trading should continue
5. Critical issues that require immediate attention

Respond with JSON in this format:
{{
   "confidence": 0.8,
   "risk_level": "low/medium/high/critical",
   "risk_warnings": ["warning1", "warning2"],
   "suggested_changes": ["change1", "change2"],
   "critical_issues": ["issue1", "issue2"],
   "analysis_summary": "summary of findings"
}}
"""
        
        return prompt
    
    def _parse_supervision_response(self, response: str) -> dict:
        """Parse AI supervision response"""
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {"error": "No valid JSON in response", "raw_response": response}
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing supervision response: {e}")
            return {"error": f"JSON decode error: {e}", "raw_response": response}

class StrategyTemplates:
    """Predefined strategy templates and patterns"""
    
    def __init__(self):
        self.templates = {
            "trend_following": {
                "indicators": ["EMA", "MACD", "ADX"],
                "entry_logic": "trend confirmation",
                "risk_management": "trailing stops"
            },
            "mean_reversion": {
                "indicators": ["RSI", "BB", "Stochastic"],
                "entry_logic": "oversold/overbought",
                "risk_management": "fixed stops"
            },
            "breakout": {
                "indicators": ["ATR", "Volume", "Support Resistance"],
                "entry_logic": "breakthrough confirmation",
                "risk_management": "volatility-based stops"
            }
        }
    
    def get_template(self, strategy_type: str) -> dict:
        """Get predefined strategy template"""
        return self.templates.get(strategy_type, {})

# Global instances
ai_strategy_generator = AIStrategyGenerator()
trading_supervision = TradingSupervision()

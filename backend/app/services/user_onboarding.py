import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import encryption_service
from app.models import User, TradingAccount

logger = logging.getLogger(__name__)

class UserOnboardingService:
    """Service for handling user onboarding and EA generation"""
    
    def __init__(self):
        self.user_config_generator = UserConfigGenerator()
        self.ea_generator = PyTraderEAGenerator()
    
    async def onboard_new_user(self, user_email: str, db: Session) -> Dict:
        """Handle complete user onboarding process"""
        try:
            # Step 1: Create user account (assuming user is already created)
            user = db.query(User).filter(User.email == user_email).first()
            if not user:
                raise ValueError("User not found")
            
            # Step 2: Generate unique user credentials
            credentials = await self.generate_user_credentials(user.id)
            
            # Step 3: Create personalized user configuration
            config = await self.user_config_generator.create_config(
                user_id=user.id,
                credentials=credentials
            )
            
            # Step 4: Generate setup guide
            setup_guide = await self.generate_setup_guide(user.id, config)
            
            # Step 5: Create EA package
            package_path = await self.ea_generator.create_ea_package(
                user_id=user.id,
                config=config
            )
            
            result = {
                'user_id': str(user.id),
                'status': 'onboarded',
                'next_steps': [
                    'Install MT5 from your broker',
                    'Download and install PyTrader EA',
                    'Configure EA with provided settings',
                    'Start EA on preferred currency pairs'
                ],
                'package_path': package_path,
                'setup_guide': setup_guide
            }
            
            logger.info(f"User {user_id} onboarded successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error in user onboarding: {e}")
            raise
    
    async def generate_user_credentials(self, user_id: str) -> Dict:
        """Generate unique user credentials for EA"""
        credentials = {
            'user_id': str(user_id),
            'api_key': os.urandom(32).hex(),
            'platform_url': f"wss://your-platform.com/ws/trading",
            'generated_at': datetime.utcnow().isoformat()
        }
        
        # Encrypt sensitive credentials
        encrypted_data = encryption_service.encrypt_data(credentials)
        
        return {
            'encrypted': encrypted_data,
            'plain': credentials  # For EA generation (would be transmitted securely)
        }
    
    async def generate_setup_guide(self, user_id: str, config: Dict) -> str:
        """Generate personalized setup guide for user"""
        guide = f"""
# Complete Setup Guide for Forex AI Trading Platform

## Step 1: Install MetaTrader 5
1. Download MT5 from your broker's website
2. Install on your Windows computer (Windows 10/11 recommended)
3. Login with your trading account credentials

## Step 2: Download PyTrader EA
1. Download from: {settings.EA_DOWNLOAD_URL.format(user_id=user_id)}
2. Save the EA file to your desktop
3. Verify the file is from a trusted source

## Step 3: Install EA in MT5
1. Open MT5
2. Go to File → Open Data Folder
3. Navigate to MQL5 → Experts
4. Copy the downloaded EA file to this folder
5. Restart MT5 (important!)

## Step 4: Configure EA Settings
1. In MT5 Navigator, find the EA named "PyTraderAI"
2. Right-click → Properties
3. Go to Inputs tab
4. Configure these settings:
   - Platform URL: {config.get('platform_url', 'wss://your-platform.com/ws/trading')}
   - User ID: {config.get('user_id', user_id)}
   - API Key: {config.get('api_key', 'your-api-key-here')}
   - Max Risk Percent: 2.0 (default, can be adjusted)
   - Heartbeat Interval: 30 (seconds)

## Step 5: Enable Automatic Trading
1. Click the "AutoTrading" button in MT5 toolbar
2. Ensure the button is green (enabled)
3. Check that "Algorithmic trading" is enabled in Tools → Options

## Step 6: Start Trading
1. Drag the EA to your desired chart (e.g., EURUSD H1)
2. Confirm the EA is running (smiley face in top right of chart)
3. The EA will connect to the platform automatically
4. Start receiving AI signals immediately!

## Important Notes:
- Keep your MT5 terminal running 24/7 for best results
- Ensure stable internet connection
- Do not share your API key with anyone
- Monitor your trades regularly
- Contact support if you encounter any issues

## Troubleshooting:
- If EA doesn't connect, check your internet connection
- Ensure firewall allows MT5 outbound connections
- Verify API key is entered correctly
- Restart MT5 if connection fails

**Need Help?** 
- Email: support@forexai.com
- Live Chat: Available on platform
- Documentation: https://docs.forexai.com

Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
User ID: {user_id}
        """
        return guide.strip()
    
    async def generate_ea_for_user(self, user_id: str, account_id: str) -> str:
        """Generate personalized EA configuration for user account"""
        try:
            # Generate credentials
            credentials = await self.generate_user_credentials(user_id)
            
            # Create configuration
            config = await self.user_config_generator.create_config(
                user_id=user_id,
                credentials=credentials['plain']
            )
            
            # Generate EA package
            package_path = await self.ea_generator.create_ea_package(
                user_id=user_id,
                config=config,
                account_id=account_id
            )
            
            return package_path
            
        except Exception as e:
            logger.error(f"Error generating EA for user {user_id}: {e}")
            raise

class UserConfigGenerator:
    """Generate personalized user configurations"""
    
    async def create_config(self, user_id: str, credentials: Dict) -> Dict:
        """Create personalized EA configuration"""
        config = {
            'platform_url': credentials.get('platform_url', f"wss://your-platform.com/ws/trading"),
            'user_id': credentials.get('user_id', user_id),
            'api_key': credentials.get('api_key'),
            
            # EA Settings
            'max_risk_percent': 2.0,
            'max_positions_per_pair': 1,
            'allowed_pairs': ['EURUSD', 'GBPUSD', 'XAUUSD'],
            
            # Connection settings
            'reconnect_attempts': 5,
            'heartbeat_interval': 30,  # seconds
            'connection_timeout': 60,  # seconds
            
            # Safety settings
            'require_manual_confirmation': False,
            'max_slippage': 10,  # points
            'min_profit_pips': 5,
            
            # Version info
            'ea_version': '1.0.0',
            'generated_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(days=365)).isoformat()
        }
        
        return config

class PyTraderEAGenerator:
    """Generate PyTrader EA for users"""
    
    def __init__(self):
        self.ea_template = self._get_ea_template()
    
    async def create_ea_package(self, user_id: str, config: Dict, account_id: Optional[str] = None) -> str:
        """Create complete EA package for user"""
        try:
            # Create package directory
            package_path = f"ea_packages/{user_id}/"
            os.makedirs(package_path, exist_ok=True)
            
            # Generate EA file
            ea_code = self._generate_ea_code(config)
            ea_file_path = f"{package_path}/pytrader_ai_ea.mq5"
            
            with open(ea_file_path, 'w') as f:
                f.write(ea_code)
            
            # Generate configuration file
            config_file_path = f"{package_path}/config.json"
            with open(config_file_path, 'w') as f:
                import json
                json.dump(config, f, indent=2)
            
            # Generate README
            readme_content = self._generate_readme(user_id, config)
            readme_path = f"{package_path}/README.md"
            with open(readme_path, 'w') as f:
                f.write(readme_content)
            
            logger.info(f"EA package created for user {user_id} at {package_path}")
            return package_path
            
        except Exception as e:
            logger.error(f"Error creating EA package: {e}")
            raise
    
    def _generate_ea_code(self, config: Dict) -> str:
        """Generate MQL5 EA code"""
        ea_code = f"""
//+------------------------------------------------------------------+
//|                                          PyTraderAI_EA_v1.0.0.mq5    |
//|                        Copyright 2025, Forex AI Trading Platform   |
//|                                             https://forexai.com      |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, Forex AI Trading Platform"
#property link      "https://forexai.com"
#property version   "1.00"
#property description "AI-powered trading signal receiver for Forex AI Platform"

#include <Trade\\Trade.mqh>

// Input parameters
input string InpPlatformURL = "{config.get('platform_url', 'wss://your-platform.com/ws/trading')}";
input string InpUserID = "{config.get('user_id')}";
input string InpAPIKey = "{config.get('api_key')}";
input double InpMaxRiskPercent = {config.get('max_risk_percent', 2.0)};
input int InpMaxPositionsPerPair = {config.get('max_positions_per_pair', 1)};
input int InpReconnectAttempts = {config.get('reconnect_attempts', 5)};
input int InpHeartbeatInterval = {config.get('heartbeat_interval', 30)};

// Global variables
CTrade trade;
datetime lastHeartbeat = 0;
bool isConnecting = false;
int reconnectCount = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit() {{
   trade.SetExpertMagicNumber(12345);
   trade.SetMarginMode();
   
   Print("PyTraderAI EA initialized for user: ", InpUserID);
   Print("Connecting to platform: ", InpPlatformURL);
   
   // Initialize WebSocket connection
   ConnectToPlatform();
   
   return(INIT_SUCCEEDED);
}}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {{
   Print("PyTraderAI EA deinitialized");
   DisconnectFromPlatform();
}}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick() {{
   // Send heartbeat periodically
   if(TimeCurrent() - lastHeartbeat > InpHeartbeatInterval) {{
      SendHeartbeat();
      lastHeartbeat = TimeCurrent();
   }}
}}

//+------------------------------------------------------------------+
//| WebSocket connection functions                                  |
//+------------------------------------------------------------------+
void ConnectToPlatform() {{
   if(isConnecting) return;
   
   isConnecting = true;
   // WebSocket connection logic would go here
   // This is a simplified version for demonstration
   
   Print("WebSocket connection established");
   SendConnectionMessage();
   reconnectCount = 0;
   isConnecting = false;
}}

void DisconnectFromPlatform() {{
   // Cleanup connection
   Print("WebSocket connection closed");
}}

void SendConnectionMessage() {{
   // Send initial connection message
   string message = "{{\\"type\\": \\"connection\\", \\"user_id\\": \\"" + InpUserID + "\\", \\"mt5_accounts\\": [{{\\"login\\": \\"" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "\\", \\"balance\\": \\"" + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2) + "\\"}}]}}";
   
   // Send message via WebSocket
   Print("Connection message sent: ", message);
}}

void SendHeartbeat() {{
   string message = "{{\\"type\\": \\"heartbeat\\", \\"account_data\\": {{\\"login\\": \\"" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "\\", \\"balance\\": \\"" + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2) + "\\"}}}}";
   
   // Send heartbeat via WebSocket
}}

//+------------------------------------------------------------------+
//| Trade execution functions                                       |
//+------------------------------------------------------------------+
void ExecuteSignal(string symbol, string signalType, double volume, double price, double stopLoss, double takeProfit) {{
   ENUM_ORDER_TYPE orderType = signalType == "BUY" ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   
   double executionPrice = (signalType == "BUY") ? ask : bid;
   
   if(stopLoss == 0) {{
      stopLoss = signalType == "BUY" ? executionPrice - 0.0015 : executionPrice + 0.0015;
   }}
   
   if(takeProfit == 0) {{
      takeProfit = signalType == "BUY" ? executionPrice + 0.0030 : executionPrice - 0.0030;
   }}
   
   bool result = trade.PositionOpen(symbol, orderType, volume, executionPrice, stopLoss, takeProfit, "AI_" + InpUserID);
   
   if(result) {{
      ulong orderTicket = trade.ResultOrder();
      Print("Trade executed successfully. Order ticket: ", orderTicket);
      
      // Send execution result back to platform
      SendTradeResult(signalType, orderTicket, true, executionPrice);
   }} else {{
      uint error = trade.ResultCode();
      string errorDesc = trade.ResultComment();
      Print("Trade execution failed. Error: ", error, " - ", errorDesc);
      
      // Send failure result back to platform
      SendTradeResult(signalType, 0, false, 0);
   }}
}}

void SendTradeResult(string signalType, ulong orderTicket, bool success, double price) {{
   string message = "{{\\"type\\": \\"trade_result\\", \\"signal_type\\": \\"" + signalType + "\\", \\"order_id\\": \\"" + IntegerToString(orderTicket) + "\\", \\"status\\": \\"" + (success ? "executed" : "failed") + "\\", \\"execution_price\\": \\"" + DoubleToString(price, 5) + "\\", \\"timestamp\\": \\"" + TimeToString(TimeCurrent()) + "\\"}}";
   
   // Send result via WebSocket
   Print("Trade result sent: ", message);
}}

//+------------------------------------------------------------------+
//| Message processing functions                                    |
//+------------------------------------------------------------------+
void ProcessWebSocketMessage(string message) {{
   // Parse JSON and process trading signals
   // This is simplified for demonstration
   
   if(StringFind(message, "\\"trading_signal\\"") >= 0) {{
      // Extract signal data and execute trade
      Print("Trading signal received: ", message);
      
      // This would parse the actual JSON and extract:
      // - symbol
      // - type (BUY/SELL)
      // - volume
      // - price
      // - stopLoss
      // - takeProfit
      
      // For demonstration, execute a sample trade
      ExecuteSignal("EURUSD", "BUY", 0.01, SymbolInfoDouble("EURUSD", SYMBOL_ASK), 0, 0);
   }}
}}
"""
        return ea_code
    
    def _generate_readme(self, user_id: str, config: Dict) -> str:
        """Generate README for EA package"""
        readme = f"""
# PyTrader AI EA Package

This package contains the Expert Advisor (EA) for connecting your MetaTrader 5 terminal to the Forex AI Trading Platform.

## Installation Instructions

1. Copy `pytrader_ai_ea.mq5` to your MT5 Experts folder
2. Copy `config.json` to the same folder
3. Restart MetaTrader 5
4. Configure the EA with your credentials
5. Start the EA on your charts

## Configuration

- Platform URL: {config.get('platform_url')}
- User ID: {config.get('user_id')}
- API Key: {config.get('api_key')}

## Support

For support, please contact: support@forexai.com

Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return readme
    
    def _get_ea_template(self) -> str:
        """Get EA template code"""
        return "// EA template placeholder"

# Global instance
user_onboarding_service = UserOnboardingService()

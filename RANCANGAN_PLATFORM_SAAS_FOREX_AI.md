# Rancangan Platform SaaS Forex Bot Trading dengan AI LLM

## 1. Executive Summary

Platform ini merupakan solusi SaaS (Software as a Service) untuk forex trading otomatis yang mengintegrasikan AI/LLM untuk strategy generation dan supervisi bot trading. Platform mengirimkan signal trading ke MetaTrader 5 yang berjalan di komputer Windows masing-masing user melalui PyTrader API connector, diperkuat dengan kemampuan AI melalui OpenRouter API.

### Fitur Utama:
- Multi-tenant architecture untuk mendukung banyak trader
- AI-powered strategy generation dan supervisi trading
- Real-time monitoring dashboard
- Backtesting dan portfolio management
- Commission-based monetization model
- Support untuk semua pair forex + XAUUSD

## 2. Arsitektur Sistem

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                          │
├─────────────────────────────────────────────────────────────────┤
│  Web Dashboard (React/Next.js)  │  Mobile App (React Native)    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (Kong/Nginx)                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
┌───────────────────────────┐   ┌───────────────────────────────┐
│    Core Trading Service   │   │     AI Strategy Service       │
│      (FastAPI/Django)     │   │        (FastAPI)              │
├───────────────────────────┤   ├───────────────────────────────┤
│  • User Management        │   │  • Strategy Generation        │
│  • Portfolio Management   │   │  • Market Analysis           │
│  • Risk Management        │   │  • Trading Supervision       │
│  • Commission Calculation │   │  • OpenRouter Integration    │
└───────────────────────────┘   └───────────────────────────────┘
                │                               │
                └───────────────┬───────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Signal Generation Layer                       │
├─────────────────────────────────────────────────────────────────┤
│   Freqtrade Core    │    Signal Manager    │   WebSocket Hub   │
│   (Modified)        │    (Custom)          │   (Signal Relay) │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Internet WebSocket                           │
│                   (Platform to Client)                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  User's Windows Computer                        │
├─────────────────────────────────────────────────────────────────┤
│  PyTrader Client    │    WebSocket Client    │   MetaTrader 5   │
│  (EA in MT5)        │    (Signal Receiver)   │   (User Instance)│
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Details

#### 2.2.1 Frontend Layer
- **Web Dashboard**: React/Next.js dengan Material-UI atau Ant Design
- **Features**:
  - Real-time trading charts (TradingView integration)
  - Portfolio overview
  - Strategy configuration
  - Backtesting interface
  - Performance analytics
  - AI chat interface untuk strategy consultation

#### 2.2.2 Backend Services

**Core Trading Service**:
```python
# Tech Stack
- Framework: FastAPI atau Django REST
- Database: PostgreSQL (user data, transactions)
- Cache: Redis (session, real-time data)
- Message Queue: RabbitMQ/Kafka
```

**AI Strategy Service**:
```python
# Integration dengan OpenRouter
- Multiple LLM support (GPT-4, Claude, etc)
- Strategy template generation
- Market sentiment analysis
- Risk assessment
- Trading signal validation
```

#### 2.2.3 Signal Generation Layer
Modified Freqtrade dengan custom signal manager:
- AI-generated custom strategies
- Signal generation dan validation
- Multi-user signal distribution
- WebSocket-based signal relay
- Risk management checks before signal transmission

**Signal Flow**: Platform generates signals → WebSocket transmission → PyTrader EA on user's MT5 receives and executes

### 2.3 Database Schema

```sql
-- Users & Authentication
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active'
);

-- Trading Accounts
CREATE TABLE trading_accounts (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    mt5_login VARCHAR(50) NOT NULL,
    broker VARCHAR(100) NOT NULL,
    account_type VARCHAR(50),
    balance DECIMAL(20, 2),
    connection_status VARCHAR(20) DEFAULT 'offline',
    websocket_connection_id VARCHAR(100),
    pytrader_ea_version VARCHAR(20),
    last_ping TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI Strategies
CREATE TABLE ai_strategies (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    llm_model VARCHAR(100),
    strategy_config JSONB,
    performance_metrics JSONB,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trading History
CREATE TABLE trades (
    id UUID PRIMARY KEY,
    account_id UUID REFERENCES trading_accounts(id),
    strategy_id UUID REFERENCES ai_strategies(id),
    symbol VARCHAR(20) NOT NULL,
    type VARCHAR(10) NOT NULL,
    volume DECIMAL(10, 2),
    open_price DECIMAL(10, 5),
    close_price DECIMAL(10, 5),
    profit_loss DECIMAL(10, 2),
    commission DECIMAL(10, 2),
    opened_at TIMESTAMP,
    closed_at TIMESTAMP
);

-- Commission Tracking
CREATE TABLE commissions (
    id UUID PRIMARY KEY,
    trade_id UUID REFERENCES trades(id),
    user_id UUID REFERENCES users(id),
    amount DECIMAL(10, 2),
    status VARCHAR(50) DEFAULT 'pending',
    processed_at TIMESTAMP
);
```

## 3. Integrasi AI/LLM dengan OpenRouter

### 3.1 Strategy Generation Flow

```python
# AI Strategy Generation Service
class AIStrategyGenerator:
    def __init__(self):
        self.openrouter_client = OpenRouterClient()
        self.strategy_templates = StrategyTemplates()
    
    async def generate_strategy(
        self,
        user_preferences: dict,
        market_conditions: dict,
        selected_model: str = "claude-3-opus"
    ) -> dict:
        """
        Generate trading strategy based on:
        - User risk profile
        - Market analysis
        - Historical performance
        """
        prompt = self.build_strategy_prompt(
            user_preferences, 
            market_conditions
        )
        
        # Call OpenRouter API with selected model
        response = await self.openrouter_client.complete(
            model=selected_model,
            prompt=prompt,
            temperature=0.7
        )
        
        # Parse and validate strategy
        strategy = self.parse_strategy_response(response)
        validated_strategy = self.validate_strategy(strategy)
        
        # Convert to Freqtrade format
        freqtrade_config = self.convert_to_freqtrade(
            validated_strategy
        )
        
        return freqtrade_config
```

### 3.2 Trading Supervision

```python
class TradingSupervision:
    def __init__(self):
        self.ai_client = OpenRouterClient()
        self.risk_manager = RiskManager()
    
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
        analysis = await self.ai_client.analyze_trading_state(
            positions=current_positions,
            market=market_data,
            performance=strategy_performance
        )
        
        recommendations = {
            'continue': analysis.confidence > 0.7,
            'adjustments': analysis.suggested_changes,
            'risk_alerts': analysis.risk_warnings,
            'stop_trading': analysis.critical_issues
        }
        
        return recommendations
```

## 4. Integration dengan MT5

### 4.1 WebSocket Signal Transmission

```python
# WebSocket Signal Manager
class SignalTransmitter:
    def __init__(self):
        self.connected_clients = {}  # user_id: websocket_connection
        self.signal_queue = asyncio.Queue()
    
    async def handle_client_connection(self, websocket, user_id):
        """Handle WebSocket connection from user's PyTrader client"""
        await websocket.accept()
        self.connected_clients[user_id] = websocket
        
        try:
            while True:
                # Receive ping/pong and account status from client
                message = await websocket.receive_json()
                if message['type'] == 'ping':
                    await self.update_account_status(user_id, message['account_data'])
                elif message['type'] == 'trade_result':
                    await self.process_trade_result(user_id, message['trade_data'])
                    
        except WebSocketDisconnect:
            del self.connected_clients[user_id]
            await self.mark_user_offline(user_id)
    
    async def send_signal_to_user(self, user_id, signal):
        """Send trading signal to specific user's MT5 via WebSocket"""
        if user_id in self.connected_clients:
            websocket = self.connected_clients[user_id]
            try:
                await websocket.send_json({
                    'type': 'trading_signal',
                    'signal': signal,
                    'timestamp': datetime.now().isoformat()
                })
                return True
            except:
                await self.handle_failed_transmission(user_id, signal)
                return False
        else:
            # Queue signal for when user reconnects
            await self.queue_signal_for_user(user_id, signal)
            return False
```

### 4.2 User-Side PyTrader Configuration

```python
# PyTrader EA - Runs on user's MT5 terminal
class PyTraderClient:
    def __init__(self, mt5_terminal, user_config):
        self.mt5 = mt5_terminal
        self.user_id = user_config['user_id']
        self.platform_url = user_config['platform_url']
        self.websocket_url = f"{user_config['platform_url']}/ws/trading/{self.user_id}"
        self.connection = None
    
    async def connect_to_platform(self):
        """Connect to platform WebSocket"""
        async with websockets.connect(self.websocket_url) as websocket:
            self.connection = websocket
            
            # Send initial connection message
            await websocket.send_json({
                'type': 'connection',
                'user_id': self.user_id,
                'mt5_accounts': self.get_connected_accounts()
            })
            
            # Listen for signals and execute trades
            async for message in websocket:
                data = json.loads(message)
                if data['type'] == 'trading_signal':
                    await self.execute_signal(data['signal'])
    
    async def execute_signal(self, signal):
        """Execute trading signal on local MT5"""
        try:
            order = self.mt5.OrderSend(
                symbol=signal['symbol'],
                type=signal['order_type'],
                volume=signal['volume'],
                price=signal['price'],
                sl=signal['stop_loss'],
                tp=signal['take_profit'],
                comment=f"AI_{signal['strategy_id']}"
            )
            
            # Send execution result back to platform
            await self.connection.send_json({
                'type': 'trade_result',
                'signal_id': signal['id'],
                'order_id': order.order,
                'status': 'executed' if order.retcode == 10009 else 'failed',
                'execution_price': order.price,
                'timestamp': datetime.now().isoformat()
            })
            
            return order
            
        except Exception as e:
            await self.connection.send_json({
                'type': 'trade_result',
                'signal_id': signal['id'],
                'error': str(e),
                'status': 'error',
                'timestamp': datetime.now().isoformat()
            })
            return None
```

### 4.3 Platform-Side Signal Management

```python
class PlatformSignalManager:
    def __init__(self):
        self.signal_transmitter = SignalTransmitter()
        self.freqtrade_engine = ModifiedFreqtrade()
    
    async def process_market_data(self, market_data):
        """Process real-time market data and generate signals"""
        for user_id in self.get_active_users():
            user_strategies = await self.get_user_strategies(user_id)
            
            for strategy in user_strategies:
                # Generate signal using Freqtrade + AI strategy
                signal = await self.freqtrade_engine.generate_signal(
                    strategy_config=strategy.config,
                    market_data=market_data
                )
                
                if signal and self.validate_signal(signal):
                    # Send signal to user's MT5
                    await self.signal_transmitter.send_signal_to_user(
                        user_id, 
                        signal
                    )
                    
                    # Log signal for tracking
                    await self.log_signal(user_id, strategy.id, signal)
    
    async def handle_trade_result(self, user_id, trade_data):
        """Handle trade execution result from user's MT5"""
        # Update database with actual trade data
        await self.update_trade_execution(trade_data)
        
        # Update account balance
        await self.sync_account_balance(user_id, trade_data['account'])
        
        # Calculate commission for profitable trade
        if trade_data['profit'] > 0:
            commission = self.calculate_commission(trade_data['profit'])
            await self.create_commission_record(user_id, commission)
```

## 5. User-Side Setup Requirements

### 5.1 User Prerequisites

Each user must have:

1. **Windows Computer** (Windows 10/11 recommended)
2. **MetaTrader 5 Terminal** installed from their broker
3. **Active MT5 Account** with trading permissions
4. **Internet Connection** for WebSocket connection

### 5.2 PyTrader EA Installation

 Users need to install the PyTrader Expert Advisor (EA) in their MT5:

```python
# Installation Steps for Users
"""
1. Download PyTrader EA from platform
2. Copy EA file to MT5 Experts folder:
   C:\Program Files\MetaTrader 5\MQL5\Experts\
3. Enable Expert Advisors in MT5
4. Enable DLL imports for EA
5. Add platform API credentials to EA settings
6. Load EA on desired forex pairs
7. Enable AutoTrading
"""
```

### 5.3 User Configuration File

```python
# User configuration - stored locally
USER_CONFIG = {
    'platform_url': 'wss://forex-ai-platform.com/ws/trading',
    'user_id': 'unique_user_id_from_platform',
    'api_key': 'platform_generated_api_key',
    
    # EA Settings
    'max_risk_percent': 2.0,
    'max_positions_per_pair': 1,
    'allowed_pairs': ['EURUSD', 'GBPUSD', 'XAUUSD'],
    
    # Connection settings
    'reconnect_attempts': 5,
    'heartbeat_interval': 30,  # seconds
    
    # Safety settings
    'require_manual_confirmation': False,
    'max_slippage': 10,
    'min_profit_pips': 5
}
```

### 5.4 Platform-Side User Onboarding

```python
class UserOnboardingService:
    def __init__(self):
        self.user_config_generator = UserConfigGenerator()
        self.ea_download_service = EADownloadService()
    
    async def onboard_new_user(self, user_email: str):
        """Handle complete user onboarding process"""
        
        # Step 1: Create user account
        user = await self.create_user_account(user_email)
        
        # Step 2: Generate unique user credentials
        credentials = await self.generate_user_credentials(user.id)
        
        # Step 3: Create personalized EA configuration
        config = await self.user_config_generator.create_config(
            user_id=user.id,
            credentials=credentials
        )
        
        # Step 4: Generate setup guide
        setup_guide = await self.generate_setup_guide(user.id, config)
        
        # Step 5: Send onboarding email
        await self.send_onboarding_email(
            user_email=user_email,
            setup_guide=setup_guide,
            download_link=f"/downloads/ea/{user.id}"
        )
        
        return {
            'user_id': user.id,
            'status': 'onboarded',
            'next_steps': [
                'Install MT5 from your broker',
                'Download and install PyTrader EA',
                'Configure EA with provided settings',
                'Start EA on preferred currency pairs'
            ]
        }
    
    async def generate_setup_guide(self, user_id: str, config: dict) -> str:
        """Generate personalized setup guide for user"""
        guide = f"""
# Complete Setup Guide for Forex AI Trading Platform

## Step 1: Install MetaTrader 5
1. Download MT5 from your broker's website
2. Install on your Windows computer
3. Login with your trading account credentials

## Step 2: Download PyTrader EA
1. Download from: https://platform.com/downloads/ea/{user_id}
2. Save the EA file to your desktop

## Step 3: Install EA in MT5
1. Open MT5
2. Go to File → Open Data Folder
3. Navigate to MQL5 → Experts
4. Copy the downloaded EA file to this folder
5. Restart MT5

## Step 4: Configure EA Settings
1. In MT5 Navigator, find the EA
2. Right-click → Properties
3. Input these settings:
   - Platform URL: {config['platform_url']}
   - User ID: {config['user_id']}
   - API Key: {config['api_key']}

## Step 5: Start Trading
1. Enable AutoTrading button in MT5
2. Drag the EA to your chart
3. Select desired timeframes
4. Start receiving AI signals!

**Need Help?** Contact support: support@platform.com
        """
        return guide
```

## 6. Deployment Architecture (Render.com)

### 6.1 Services Configuration

```yaml
# render.yaml
services:
  # Web Service - API Backend
  - type: web
    name: forex-ai-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn main:app
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: forex-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          type: redis
          name: forex-cache
          property: connectionString
      - key: OPENROUTER_API_KEY
        sync: false
    
  # Worker Service - Trading Engine
  - type: worker
    name: trading-engine
    env: python
    buildCommand: pip install -r requirements-trading.txt
    startCommand: python trading_worker.py
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: forex-db
          property: connectionString
    
  # Static Site - Frontend
  - type: static
    name: forex-ai-frontend
    buildCommand: npm run build
    staticPublishPath: ./build
    
databases:
  - name: forex-db
    plan: standard
    databaseName: forexai
    user: forexuser
    
  - name: forex-cache
    plan: standard
    type: redis
```

### 6.2 Scalability Strategy

```python
# Horizontal Scaling Configuration
SCALING_CONFIG = {
    'min_instances': 1,
    'max_instances': 10,
    'target_cpu': 70,
    'target_memory': 80,
    'scale_up_threshold': {
        'active_users': 50,
        'trades_per_minute': 100
    }
}

# Load Balancing
LOAD_BALANCER_CONFIG = {
    'algorithm': 'round_robin',
    'health_check_path': '/health',
    'health_check_interval': 30
}
```

## 7. Security Implementation

### 7.1 Authentication & Authorization

```python
# JWT-based Authentication
from fastapi_jwt_auth import AuthJWT

class AuthService:
    def __init__(self):
        self.jwt_secret = os.getenv('JWT_SECRET')
        self.jwt_algorithm = 'HS256'
        self.access_token_expires = timedelta(hours=1)
        self.refresh_token_expires = timedelta(days=30)
    
    def create_tokens(self, user_id: str) -> dict:
        """Create access and refresh tokens"""
        access_token = AuthJWT().create_access_token(
            subject=user_id,
            expires_time=self.access_token_expires
        )
        
        refresh_token = AuthJWT().create_refresh_token(
            subject=user_id,
            expires_time=self.refresh_token_expires
        )
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token
        }
```

### 7.2 Data Encryption

```python
# Encryption for sensitive data
from cryptography.fernet import Fernet

class EncryptionService:
    def __init__(self):
        self.key = os.getenv('ENCRYPTION_KEY').encode()
        self.cipher = Fernet(self.key)
    
    def encrypt_mt5_credentials(self, credentials: dict) -> str:
        """Encrypt MT5 login credentials"""
        data = json.dumps(credentials).encode()
        encrypted = self.cipher.encrypt(data)
        return encrypted.decode()
    
    def decrypt_mt5_credentials(self, encrypted: str) -> dict:
        """Decrypt MT5 login credentials"""
        decrypted = self.cipher.decrypt(encrypted.encode())
        return json.loads(decrypted.decode())
```

## 8. Commission System

### 8.1 Commission Calculation

```python
class CommissionCalculator:
    def __init__(self):
        self.base_commission_rate = 0.001  # 0.1% per trade
        self.profit_commission_rate = 0.10  # 10% dari profit
    
    def calculate_commission(self, trade: dict) -> dict:
        """Calculate commission for completed trade"""
        commission = {
            'trade_id': trade['id'],
            'volume_commission': trade['volume'] * self.base_commission_rate,
            'profit_commission': 0
        }
        
        if trade['profit_loss'] > 0:
            commission['profit_commission'] = (
                trade['profit_loss'] * self.profit_commission_rate
            )
        
        commission['total'] = (
            commission['volume_commission'] + 
            commission['profit_commission']
        )
        
        return commission
```

### 8.2 Commission Settlement

```python
class CommissionSettlement:
    async def process_daily_commissions(self):
        """Process and settle daily commissions"""
        pending_commissions = await self.get_pending_commissions()
        
        for commission in pending_commissions:
            # Calculate platform fee
            platform_fee = commission['total']
            
            # Update user balance
            await self.update_user_balance(
                commission['user_id'],
                -platform_fee
            )
            
            # Mark commission as processed
            await self.mark_commission_processed(
                commission['id']
            )
            
            # Generate invoice if needed
            await self.generate_commission_invoice(commission)
```

## 9. Monitoring & Analytics

### 9.1 Real-time Monitoring

```python
# WebSocket for real-time updates
from fastapi import WebSocket

class TradingWebSocket:
    def __init__(self):
        self.connections = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.connections[user_id] = websocket
    
    async def broadcast_trade_update(self, user_id: str, trade_data: dict):
        """Send real-time trade updates to user"""
        if user_id in self.connections:
            websocket = self.connections[user_id]
            await websocket.send_json({
                'type': 'trade_update',
                'data': trade_data,
                'timestamp': datetime.now().isoformat()
            })
    
    async def send_market_data(self, market_data: dict):
        """Broadcast market data to all connected users"""
        for user_id, websocket in self.connections.items():
            await websocket.send_json({
                'type': 'market_update',
                'data': market_data
            })
```

### 9.2 Analytics Dashboard

```python
class AnalyticsService:
    async def get_user_analytics(self, user_id: str) -> dict:
        """Generate comprehensive analytics for user"""
        analytics = {
            'performance': await self.calculate_performance_metrics(user_id),
            'risk_metrics': await self.calculate_risk_metrics(user_id),
            'strategy_performance': await self.analyze_strategies(user_id),
            'profit_loss': await self.calculate_pnl(user_id),
            'commission_paid': await self.get_commission_history(user_id)
        }
        
        return analytics
    
    async def calculate_performance_metrics(self, user_id: str) -> dict:
        """Calculate trading performance metrics"""
        trades = await self.get_user_trades(user_id)
        
        return {
            'total_trades': len(trades),
            'win_rate': self.calculate_win_rate(trades),
            'average_profit': self.calculate_average_profit(trades),
            'sharpe_ratio': self.calculate_sharpe_ratio(trades),
            'max_drawdown': self.calculate_max_drawdown(trades),
            'profit_factor': self.calculate_profit_factor(trades)
        }
```

## 10. API Endpoints

### 10.1 Core API Structure

```python
# Main API endpoints
from fastapi import FastAPI, Depends, HTTPException
from typing import List

app = FastAPI(title="Forex AI Trading Platform")

# User Management
@app.post("/api/v1/auth/register")
async def register_user(user_data: UserCreate) -> UserResponse:
    """Register new user"""
    pass

@app.post("/api/v1/auth/login")
async def login_user(credentials: LoginRequest) -> TokenResponse:
    """User login"""
    pass

# Trading Account Management
@app.post("/api/v1/accounts/connect")
async def connect_mt5_account(
    account: MT5AccountCreate,
    current_user: User = Depends(get_current_user)
) -> AccountResponse:
    """Connect MT5 account"""
    pass

# Strategy Management
@app.post("/api/v1/strategies/generate")
async def generate_ai_strategy(
    preferences: StrategyPreferences,
    current_user: User = Depends(get_current_user)
) -> StrategyResponse:
    """Generate AI trading strategy"""
    pass

@app.get("/api/v1/strategies")
async def list_strategies(
    current_user: User = Depends(get_current_user)
) -> List[StrategyResponse]:
    """List user strategies"""
    pass

# Trading Operations
@app.post("/api/v1/trading/start")
async def start_trading(
    config: TradingConfig,
    current_user: User = Depends(get_current_user)
) -> TradingResponse:
    """Start automated trading"""
    pass

@app.post("/api/v1/trading/stop")
async def stop_trading(
    account_id: str,
    current_user: User = Depends(get_current_user)
) -> StatusResponse:
    """Stop trading for account"""
    pass

# Analytics
@app.get("/api/v1/analytics/dashboard")
async def get_dashboard_data(
    current_user: User = Depends(get_current_user)
) -> DashboardResponse:
    """Get dashboard analytics"""
    pass

# WebSocket endpoint
@app.websocket("/ws/trading/{user_id}")
async def trading_websocket(
    websocket: WebSocket,
    user_id: str
):
    """WebSocket for real-time updates"""
    await websocket_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Process incoming messages
    except WebSocketDisconnect:
        websocket_manager.disconnect(user_id)
```

## 11. Development Roadmap

### Phase 1: MVP (Month 1-2)
- [ ] Basic user authentication
- [ ] MT5 connection via PyTrader
- [ ] Simple AI strategy generation
- [ ] Basic trading execution
- [ ] Simple dashboard

### Phase 2: Core Features (Month 3-4)
- [ ] Advanced AI strategy generation
- [ ] Backtesting integration
- [ ] Risk management system
- [ ] Commission tracking
- [ ] Real-time monitoring

### Phase 3: Enhancement (Month 5-6)
- [ ] Multi-account support
- [ ] Advanced analytics
- [ ] Mobile app
- [ ] Social trading features
- [ ] Advanced AI supervision

### Phase 4: Scaling (Month 7+)
- [ ] Performance optimization
- [ ] Additional broker support
- [ ] Advanced ML models
- [ ] Regulatory compliance
- [ ] International expansion

## 12. Technology Stack Summary

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI/Django
- **Database**: PostgreSQL
- **Cache**: Redis
- **Message Queue**: RabbitMQ/Kafka
- **Trading Engine**: Modified Freqtrade
- **MT5 Connector**: PyTrader API

### Frontend
- **Framework**: React/Next.js
- **UI Library**: Material-UI/Ant Design
- **Charts**: TradingView/Lightweight Charts
- **State Management**: Redux/Zustand
- **Real-time**: Socket.io/Native WebSocket

### AI/ML
- **LLM Provider**: OpenRouter API
- **Models**: GPT-4, Claude, Llama (flexible)
- **ML Libraries**: scikit-learn, TensorFlow/PyTorch
- **Data Processing**: pandas, numpy

### Infrastructure
- **Hosting**: Render.com
- **Container**: Docker
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus/Grafana
- **Logging**: ELK Stack

## 13. Risk Considerations

### Technical Risks
1. **MT5 Connection Stability**: Implement redundant connections
2. **AI Model Reliability**: Fallback strategies, human oversight
3. **Data Security**: Encryption, secure storage
4. **System Downtime**: High availability setup

### Business Risks
1. **Regulatory Compliance**: Legal consultation needed
2. **Market Volatility**: Risk management protocols
3. **User Trust**: Transparent reporting, audit trails
4. **Competition**: Unique AI features differentiation

## 14. Testing Strategy

```python
# Testing framework
import pytest
from unittest.mock import Mock, patch

class TestTradingSystem:
    @pytest.fixture
    def mock_mt5_connection(self):
        """Mock MT5 connection for testing"""
        return Mock(spec=MT5Connector)
    
    @pytest.fixture
    def mock_ai_service(self):
        """Mock AI service for testing"""
        return Mock(spec=AIStrategyGenerator)
    
    async def test_strategy_generation(self, mock_ai_service):
        """Test AI strategy generation"""
        mock_ai_service.generate_strategy.return_value = {
            'strategy_name': 'test_strategy',
            'indicators': ['RSI', 'MACD'],
            'risk_level': 'medium'
        }
        
        result = await mock_ai_service.generate_strategy(
            user_preferences={'risk': 'medium'},
            market_conditions={'trend': 'bullish'}
        )
        
        assert result['strategy_name'] == 'test_strategy'
        assert 'RSI' in result['indicators']
    
    async def test_trade_execution(self, mock_mt5_connection):
        """Test trade execution flow"""
        mock_mt5_connection.execute_trade.return_value = {
            'order_id': '12345',
            'status': 'executed'
        }
        
        signal = {
            'symbol': 'EURUSD',
            'type': 'BUY',
            'volume': 0.1
        }
        
        result = mock_mt5_connection.execute_trade('test_login', signal)
        
        assert result['order_id'] == '12345'
        assert result['status'] == 'executed'
```

## 15. Conclusion

Platform SaaS Forex Bot Trading dengan AI LLM ini dirancang untuk memberikan solusi trading otomatis yang cerdas, scalable, dan user-friendly. Dengan mengintegrasikan teknologi AI terkini melalui OpenRouter, sistem ini dapat menghasilkan dan mengawasi strategi trading secara adaptif sesuai kondisi pasar.

Key success factors:
1. **Reliable MT5 Integration**: Koneksi stabil dengan multiple broker
2. **Smart AI Strategy**: Flexible LLM selection untuk optimal performance
3. **Robust Risk Management**: Comprehensive risk controls
4. **Transparent Commission**: Fair commission structure
5. **Excellent UX**: Intuitive dashboard dan monitoring

Platform ini memiliki potensi besar untuk disrupting traditional forex trading dengan mendemokratisasi akses ke advanced AI trading strategies.

---

**Document Version**: 1.0
**Created**: October 2025
**Last Updated**: October 2025
**Author**: AI Trading Platform Team

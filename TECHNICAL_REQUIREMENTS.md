# Technical Requirements & Setup Guide

## System Requirements

### Development Environment
- **OS**: Ubuntu 20.04+ / macOS 12+ / Windows 10+ with WSL2
- **Python**: 3.11 or higher
- **Node.js**: 18.x or higher
- **Docker**: 20.10+ and Docker Compose 2.x
- **PostgreSQL**: 14+
- **Redis**: 7.0+
- **Git**: 2.x

### MetaTrader 5 Requirements (Client-Side)
- **MT5 Terminal**: Latest version - User Responsibility
- **Windows Computer**: Windows 10/11 - User's Local Machine
- **Broker Account**: User's own broker account
- **PyTrader EA**: User-installed Expert Advisor

**Note**: Platform does NOT host or manage MT5. Users install MT5 on their own computers.

## Installation Dependencies

### Backend Dependencies

```bash
# requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
python-jose[cryptography]==3.3.0
python-multipart==0.0.6
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9
redis==5.0.1
celery==5.3.4
pydantic==2.5.0
pydantic-settings==2.1.0

# Trading specific
freqtrade==2025.8
ccxt==4.1.50
pandas==2.1.4
numpy==1.26.2
ta-lib==0.4.28
scikit-learn==1.3.2

# AI/LLM
openai==1.5.0
langchain==0.0.350
tiktoken==0.5.2
aiohttp==3.9.1

# WebSocket Communication
websocket-client==1.7.0
websockets==12.0
pyzmq==25.1.2

# PyTrader Client Support (User-side EA references)
# Note: PyTrader EA is distributed to users separately

# Monitoring & Logging
prometheus-client==0.19.0
python-json-logger==2.0.7
sentry-sdk==1.39.1

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
httpx==0.25.2
faker==21.0.0
```

### Frontend Dependencies

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "next": "^14.0.4",
    "@mui/material": "^5.15.0",
    "@emotion/react": "^11.11.3",
    "@emotion/styled": "^11.11.0",
    "axios": "^1.6.3",
    "socket.io-client": "^4.7.2",
    "@reduxjs/toolkit": "^2.0.1",
    "react-redux": "^9.0.4",
    "lightweight-charts": "^4.1.0",
    "recharts": "^2.10.3",
    "react-hook-form": "^7.48.2",
    "react-query": "^3.39.3",
    "date-fns": "^3.0.6",
    "uuid": "^9.0.1"
  },
  "devDependencies": {
    "@types/react": "^18.2.45",
    "@types/node": "^20.10.5",
    "typescript": "^5.3.3",
    "eslint": "^8.56.0",
    "prettier": "^3.1.1",
    "@testing-library/react": "^14.1.2",
    "jest": "^29.7.0"
  }
}
```

## Project Structure

```
saas-forex-ai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── auth.py
│   │   │   │   │   ├── trading.py
│   │   │   │   │   ├── strategies.py
│   │   │   │   │   └── analytics.py
│   │   │   │   └── router.py
│   │   │   └── dependencies.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── database.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── trade.py
│   │   │   └── strategy.py
│   │   ├── services/
│   │   │   ├── ai_service.py
│   │   │   ├── websocket_transmitter.py
│   │   │   ├── signal_manager.py
│   │   │   └── commission_service.py
│   │   └── main.py
│   ├── trading/
│   │   ├── freqtrade_custom/
│   │   │   ├── strategies/
│   │   │   └── config/
│   │   ├── signal_generator/
│   │   │   ├── freqtrade_adapter.py
│   │   │   └── signal_processor.py
│   │   └── signals/
│   ├── tests/
│   ├── alembic/
│   ├── docker/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard/
│   │   │   ├── Trading/
│   │   │   ├── Analytics/
│   │   │   └── common/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── store/
│   │   └── utils/
│   ├── public/
│   ├── package.json
│   └── next.config.js
├── infrastructure/
│   ├── docker-compose.yml
│   ├── kubernetes/
│   └── terraform/
├── scripts/
│   ├── setup.sh
│   ├── deploy.sh
│   └── test.sh
└── docs/
```

## Environment Variables

```bash
# .env.development
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/forexai_dev
REDIS_URL=redis://localhost:6379/0

# Security
JWT_SECRET=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here
API_KEY=your-api-key-here

# OpenRouter AI
OPENROUTER_API_KEY=your-openrouter-api-key
DEFAULT_AI_MODEL=claude-3-opus

# WebSocket Configuration
WEBSOCKET_SERVER_PORT=8765
CLIENT_HEARTBEAT_INTERVAL=30
CONNECTION_TIMEOUT=60

# User EA Configuration
EA_DOWNLOAD_URL=https://platform.com/downloads/ea/{user_id}
SETUP_GUIDE_URL=https://platform.com/setup/{user_token}

# Trading Config
MAX_OPEN_TRADES=10
RISK_PER_TRADE=0.01
DEFAULT_TIMEFRAME=1h
COMMISSION_RATE=0.001

# External Services
SENTRY_DSN=your-sentry-dsn
STRIPE_API_KEY=your-stripe-key
SENDGRID_API_KEY=your-sendgrid-key

# Development
DEBUG=true
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000
```

## Setup Instructions

### 1. Clone and Initial Setup

```bash
# Clone repository
git clone https://github.com/yourusername/saas-forex-ai.git
cd saas-forex-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install Python dependencies
pip install -r backend/requirements.txt

# Install Node dependencies
cd frontend
npm install
cd ..
```

### 2. Database Setup

```bash
# Start PostgreSQL and Redis using Docker
docker-compose up -d postgres redis

# Run database migrations
cd backend
alembic upgrade head

# Create initial admin user
python scripts/create_admin.py
```

### 3. WebSocket Signal Setup

```python
# scripts/setup_websocket.py
import asyncio
import websockets
import json

async def test_websocket():
    """Test WebSocket signal transmission"""
    uri = "ws://localhost:8765/test"
    
    try:
        async with websockets.connect(uri) as websocket:
            # Send test signal
            test_signal = {
                'type': 'trading_signal',
                'user_id': 'test_user',
                'signal': {
                    'symbol': 'EURUSD',
                    'type': 'BUY',
                    'volume': 0.1,
                    'price': 1.0500
                }
            }
            
            await websocket.send(json.dumps(test_signal))
            response = await websocket.recv()
            
            print("✅ WebSocket test successful")
            print(f"Response: {response}")
            return True
            
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_websocket())
```

### 4. User Onboarding Setup

```python
# scripts/create_user_ea.py
import uuid
import os
from app.services.user_onboarding import UserOnboardingService

def create_user_ea_package(user_email: str):
    """Create and package EA for new user"""
    
    # Generate unique user configuration
    user_config = {
        'user_id': str(uuid.uuid4()),
        'api_key': os.urandom(32).hex(),
        'platform_url': 'wss://your-platform.com/ws/trading',
        'max_risk_percent': 2.0,
        'heartbeat_interval': 30
    }
    
    # Generate personalized EA
    ea_file = generate_pytader_ea(user_config)
    
    # Create setup guide
    setup_guide = generate_setup_guide(user_config)
    
    # Package for download
    package_path = f"ea_packages/{user_config['user_id']}/"
    os.makedirs(package_path, exist_ok=True)
    
    with open(f"{package_path}/pytrader_ea.mq5", 'w') as f:
        f.write(ea_file)
    
    with open(f"{package_path}/setup_guide.md", 'w') as f:
        f.write(setup_guide)
    
    # Send onboarding email
    send_onboarding_email(user_email, package_path)
    
    return package_path

# Example usage
# create_user_ea_package("user@example.com")
```

### 4. Freqtrade Configuration

```json
// config/freqtrade_config.json
{
    "max_open_trades": 10,
    "stake_currency": "USD",
    "stake_amount": 100,
    "tradable_balance_ratio": 0.99,
    "fiat_display_currency": "USD",
    "dry_run": true,
    "dry_run_wallet": 10000,
    "cancel_open_orders_on_exit": false,
    "trading_mode": "spot",
    "margin_mode": "",
    "unfilledtimeout": {
        "entry": 10,
        "exit": 10,
        "exit_timeout_count": 0,
        "unit": "minutes"
    },
    "entry_pricing": {
        "price_side": "same",
        "use_order_book": true,
        "order_book_top": 1,
        "price_last_balance": 0.0,
        "check_depth_of_market": {
            "enabled": false,
            "bids_to_ask_delta": 1
        }
    },
    "exit_pricing": {
        "price_side": "same",
        "use_order_book": true,
        "order_book_top": 1
    },
    "exchange": {
        "name": "binance",
        "key": "",
        "secret": "",
        "ccxt_config": {},
        "ccxt_async_config": {},
        "pair_whitelist": [],
        "pair_blacklist": []
    },
    "pairlists": [
        {
            "method": "VolumePairList",
            "number_assets": 20,
            "sort_key": "quoteVolume",
            "min_value": 0,
            "refresh_period": 1800
        }
    ],
    "telegram": {
        "enabled": false
    },
    "api_server": {
        "enabled": true,
        "listen_ip_address": "127.0.0.1",
        "listen_port": 8080,
        "verbosity": "error",
        "enable_openapi": false,
        "jwt_secret_key": "somethingrandom",
        "ws_token": "your_ws_token",
        "CORS_origins": [],
        "username": "freqtrader",
        "password": "freqtrader"
    },
    "bot_name": "freqtrade",
    "initial_state": "stopped",
    "force_entry_enable": false,
    "internals": {
        "process_throttle_secs": 5
    }
}
```

### 5. Development Workflow

```bash
# Terminal 1 - Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev

# Terminal 3 - Celery Worker
cd backend
celery -A app.worker worker --loglevel=info

# Terminal 4 - Celery Beat
cd backend
celery -A app.worker beat --loglevel=info

# Terminal 5 - Trading Engine
cd backend/trading
python trading_engine.py
```

## Docker Development Setup

```yaml
# docker-compose.development.yml
version: '3.8'

services:
  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_USER: forexai
      POSTGRES_PASSWORD: forexai123
      POSTGRES_DB: forexai_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql://forexai:forexai123@postgres:5432/forexai_dev
      - REDIS_URL=redis://redis:6379/0
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    command: npm run dev

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql://forexai:forexai123@postgres:5432/forexai_dev
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    command: celery -A app.worker worker --loglevel=info

volumes:
  postgres_data:
```

## API Testing with Postman

```json
// postman_collection.json
{
  "info": {
    "name": "Forex AI Trading API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Authentication",
      "item": [
        {
          "name": "Register User",
          "request": {
            "method": "POST",
            "header": [],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"email\": \"test@example.com\",\n  \"username\": \"testuser\",\n  \"password\": \"Test123456!\"\n}",
              "options": {
                "raw": {
                  "language": "json"
                }
              }
            },
            "url": {
              "raw": "{{base_url}}/api/v1/auth/register",
              "host": ["{{base_url}}"],
              "path": ["api", "v1", "auth", "register"]
            }
          }
        },
        {
          "name": "Login",
          "request": {
            "method": "POST",
            "header": [],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"username\": \"testuser\",\n  \"password\": \"Test123456!\"\n}",
              "options": {
                "raw": {
                  "language": "json"
                }
              }
            },
            "url": {
              "raw": "{{base_url}}/api/v1/auth/login",
              "host": ["{{base_url}}"],
              "path": ["api", "v1", "auth", "login"]
            }
          }
        }
      ]
    }
  ]
}
```

## Testing Strategy

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_trading.py

# Run integration tests
pytest tests/integration/

# Run with verbose output
pytest -v -s
```

## Performance Optimization

### Database Optimization
```sql
-- Create indexes for frequently queried columns
CREATE INDEX idx_trades_user_id ON trades(user_id);
CREATE INDEX idx_trades_created_at ON trades(created_at);
CREATE INDEX idx_strategies_user_id ON ai_strategies(user_id);
CREATE INDEX idx_commissions_status ON commissions(status);

-- Partitioning for large tables
CREATE TABLE trades_2025_q1 PARTITION OF trades
FOR VALUES FROM ('2025-01-01') TO ('2025-04-01');
```

### Redis Caching Strategy
```python
# Cache frequently accessed data
CACHE_CONFIG = {
    'user_profile': 300,  # 5 minutes
    'account_balance': 60,  # 1 minute
    'market_data': 10,  # 10 seconds
    'strategy_list': 600,  # 10 minutes
    'analytics': 300,  # 5 minutes
}
```

## Monitoring Setup

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'backend'
    static_configs:
      - targets: ['localhost:8000']
    
  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']
    
  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']
```

## Troubleshooting Guide

### Common Issues and Solutions

1. **MT5 Connection Issues**
```python
# Check MT5 terminal is running
# Verify EA is properly installed
# Check firewall settings
# Verify credentials
```

2. **Database Connection**
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
psql -h localhost -U forexai -d forexai_dev
```

3. **Redis Connection**
```bash
# Check Redis is running
redis-cli ping
# Should return PONG
```

## Security Checklist

- [ ] All secrets in environment variables
- [ ] HTTPS enabled in production
- [ ] Rate limiting implemented
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention
- [ ] XSS protection
- [ ] CORS properly configured
- [ ] JWT token expiration
- [ ] Password hashing with bcrypt
- [ ] API key rotation policy

---

**Document Version**: 1.0
**Created**: October 2025
**Author**: AI Trading Platform Team

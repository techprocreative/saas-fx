# Development Guidelines & Agent Constraints

## 🎯 Project Mandate

This document ensures all development activities align with the **SaaS Forex AI Trading Platform** architectural design and specifications. All AI agents and developers must follow these guidelines strictly.

## 📋 Core Architecture Requirements

### 1. **Technology Stack Enforcement**
- **Backend**: Python 3.11+ with FastAPI (NOT Django/Flask)
- **Frontend**: Next.js 14+ with TypeScript (NOT plain React)
- **Database**: PostgreSQL with SQLAlchemy 2.0+ (NOT MongoDB/MySQL)
- **AI Integration**: OpenRouter API only (NOT OpenAI direct)
- **Trading Engine**: Modified Freqtrade core (NOT any other trading library)

### 2. **System Architecture Compliance**
```
FORBIDDEN: Direct broker API integration
REQUIRED: WebSocket-based signal transmission to PyTrader EA
FORBIDDEN: Client-side MT5 hosting
REQUIRED: User-side MT5 with custom EA installation
FORBIDDEN: Real money without risk management
REQUIRED: Commission-based monetization tracking
```

### 3. **MT5 Integration Protocol**
- **Signal Flow**: Platform → WebSocket → PyTrader EA → MT5
- **User Responsibility**: MT5 installation, broker account, EA configuration
- **Platform Responsibility**: Signal generation, monitoring, analytics
- **Communication Method**: JSON WebSocket messages only

## 🚫 Development Restrictions

### 1. **Prohibited Technologies**
- ❌ Direct database connections from frontend
- ❌ State management libraries (Redux only, NOT Zustand/Context)
- ❌ Any trading libraries other than Freqtrade
- ❌ Direct MT5 API calls from backend
- ❌ WebSocket libraries other than native websockets/pyzmq
- ❌ AI providers other than OpenRouter

### 2. ** prohibited Functionalities**
- ❌ Hosting MT5 terminals on platform
- ❌ Managing user broker credentials on server
- ❌ Direct order execution without user approval
- ❌ Modifications to core trading risk parameters
- ❌ Commission calculation changes without approval

## ✅ Required Implementations

### 1. **Mandatory Features**
- [ ] WebSocket signal transmission to PyTrader
- [ ] OpenRouter AI integration for strategy generation
- [ ] Multi-tenant user isolation
- [ ] Real-time trading monitoring
- [ ] Commission tracking system
- [ ] Risk management enforcement
- [ ] Performance analytics dashboard

### 2. **Database Schema Compliance**
All database changes must follow this structure:
```sql
-- Required tables (no modifications to core fields)
users (id, email, username, password_hash, created_at, status)
trading_accounts (id, user_id, mt5_login, broker, balance, connection_status)
ai_strategies (id, user_id, name, llm_model, strategy_config, status)
trades (id, account_id, strategy_id, symbol, type, volume, profit_loss)
commissions (id, trade_id, user_id, amount, status, processed_at)
```

### 3. **API Endpoints Structure**
Follow these exact endpoint patterns:
```python
/api/v1/auth/*          # Authentication
/api/v1/accounts/*      # MT5 account management
/api/v1/strategies/*    # AI strategy operations
/api/v1/trading/*       # Trading operations
/api/v1/analytics/*     # Performance data
/ws/trading/{user_id}   # WebSocket endpoint
```

## 🔧 Development Workflow

### 1. **Environment Setup Check**
Before any development:
```bash
# Verify required stack
python -m fastapi --version  # Must be fastapi
npm list next               # Must be Next.js
docker -v                   # Required for development
```

### 2. **Code Review Checklist**
Every PR must validate:
- [ ] No direct MT5 API calls
- [ ] OpenRouter API usage only
- [ ] WebSocket signal implementation
- [ ] Multi-tenant data isolation
- [ ] Risk management integration
- [ ] Commission tracking
- [ ] Database schema compliance

### 3. **Testing Requirements**
```python
# Required test files
backend/tests/test_trading_signals.py
backend/tests/test_ai_strategies.py
backend/tests/test_websocket_transmission.py
frontend/tests/test_trading_dashboard.tsx
```

## 📊 Performance & Scaling Rules

### 1. **Rate Limiting**
- Max 100 signals per user per minute
- WebSocket connection limit: 10 concurrent per user
- API calls: 1000 per hour per user

### 2. **Database Optimization**
```python
# Required indexes
CREATE INDEX idx_trades_user_id ON trades(user_id);
CREATE INDEX idx_strategies_user_id ON ai_strategies(user_id);
CREATE INDEX idx_commissions_user_id ON commissions(user_id);
```

### 3. **Caching Strategy**
- User sessions: Redis (5 min TTL)
- Market data: Redis (10 sec TTL)
- Strategy lists: Redis (1 hour TTL)

## 🔒 Security Compliance

### 1. **Authentication**
```python
# Required JWT structure
{
  "user_id": "uuid",
  "exp": "timestamp",
  "iat": "timestamp",
  "permissions": ["trading", "analytics"]
}
```

### 2. **Data Encryption**
- MT5 credentials: Encrypted at rest
- WebSocket communications: WSS only
- API communications: HTTPS only

### 3. **User Data Isolation**
- Row-level security on all tables
- User ID check on all database queries
- No cross-user data access

## 🎨 Frontend Constraints

### 1. **UI Framework**
- Material-UI v5+ only (NOT Ant Design, Chakra)
- Chart library: Lightweight Charts v4+ only
- Real-time updates: Native WebSocket

### 2. **Component Structure**
```
src/components/Dashboard/*   # Dashboard components
src/components/Trading/*     # Trading interface
src/components/Analytics/*   # Charts and analytics
src/components/common/*      # Shared components
```

### 3. **State Management**
```typescript
// Required Redux structure
store/authSlice.ts     # Authentication state
store/tradingSlice.ts  # Trading operations
store/analyticsSlice.ts # Analytics data
```

## 📝 Documentation Requirements

### 1. **API Documentation**
- OpenAPI/Swagger required for all endpoints
- WebSocket message schemas documented
- Error response examples provided

### 2. **Code Documentation**
```python
# Required docstring format
async def generate_strategy(
    user_preferences: dict,
    market_conditions: dict,
    selected_model: str = "claude-3-opus"
) -> dict:
    """
    Generate AI trading strategy using OpenRouter.
    
    Args:
        user_preferences: User risk profile and preferences
        market_conditions: Current market analysis data
        selected_model: OpenRouter model to use
        
    Returns:
        Freqtrade-compatible strategy configuration
        
    Raises:
        AIServiceError: When AI service is unavailable
        ValidationError: When input parameters are invalid
    """
```

## 🚨 Deviation Protocol

### 1. **Change Request Process**
Any deviation from this document requires:
1. Formal change request document
2. Architecture team approval
3. Impact assessment
4. Updated documentation

### 2. **Emergency Exceptions**
For critical fixes requiring deviation:
1. Document the deviation immediately
2. Schedule a follow-up review
3. Address within 48 hours

## 🔍 Validation Checklist

### Before Commit:
- [ ] Follows FastAPI + SQLAlchemy patterns
- [ ] Uses OpenRouter for AI operations
- [ ] Implements WebSocket for MT5 signals
- [ ] Maintains multi-tenant isolation
- [ ] Includes proper error handling
- [ ] Has corresponding tests
- [ ] Documented with examples

### After Implementation:
- [ ] WebSocket connection stable
- [ ] AI strategies generate correctly
- [ ] Commission tracking accurate
- [ ] Risk management enforced
- [ ] Performance within limits
- [ ] Security compliance verified

---

**Last Updated**: 2025-01-18  
**Next Review**: 2025-02-18  
**Approved By**: Architecture Team

> **⚠️ CRITICAL**: Any development not following these guidelines will be rejected. This platform's success depends on strict adherence to the stated architecture and business model.

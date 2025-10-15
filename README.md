# SaaS Forex AI Trading Platform 🤖💹

Platform SaaS trading forex otomatis berbasis AI yang mengirimkan signal trading ke MetaTrader 5 user melalui WebSocket connection, diperkuat dengan machine learning untuk strategy generation dan supervision.

## 🌟 Features

### Core Features
- ✅ **Multi-tenant Architecture** - Support 10-100 concurrent users
- ✅ **AI Strategy Generation** - Generate trading strategy menggunakan LLM (GPT-4, Claude, etc.)
- ✅ **Signal Transmission** - Kirim signal ke MT5 user via WebSocket + PyTrader EA
- ✅ **Real-time Monitoring** - Dashboard untuk monitoring trading real-time
- ✅ **Backtesting** - Test strategy dengan historical data
- ✅ **Portfolio Management** - Manage multiple trading accounts
- ✅ **Risk Management** - Automated stop loss, take profit, position sizing
- ✅ **Commission System** - Commission-based revenue model (0.1% per trade + 10% profit share)

### Supported Instruments
- All Forex Pairs (EUR/USD, GBP/USD, etc.)
- XAUUSD (Gold)
- Flexible timeframes (M1, M5, M15, H1, H4, D1)

### AI Capabilities
- Strategy generation based on market conditions
- Trading supervision and anomaly detection
- Risk assessment and management
- Performance optimization
- Market sentiment analysis

## 🚀 Quick Start

### Prerequisites

**For Platform:**
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 14+
- Redis 7+

**For Users:**
- Windows Computer (Windows 10/11)
- MetaTrader 5 Terminal (user-installed)
- Active MT5 Trading Account
- Internet Connection

### Installation

1. **Clone Repository**
```bash
git clone https://github.com/yourusername/saas-forex-ai.git
cd saas-forex-ai
```

2. **Setup Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

3. **Setup Frontend**
```bash
cd frontend
npm install
```

4. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Start Services with Docker**
```bash
docker-compose up -d
```

6. **Run Migrations**
```bash
cd backend
alembic upgrade head
```

7. **Start Development Servers**
```bash
# Backend (Terminal 1)
cd backend
uvicorn app.main:app --reload

# Frontend (Terminal 2)
cd frontend
npm run dev

# Worker (Terminal 3)
cd backend
celery -A app.worker worker --loglevel=info
```

Access the application at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 📁 Project Structure

```
saas-forex-ai/
├── backend/           # Python FastAPI backend
├── frontend/          # React/Next.js frontend
├── infrastructure/    # Docker, K8s, Terraform configs
├── scripts/          # Utility scripts
└── docs/             # Documentation
```

## 🔧 Configuration

### OpenRouter AI Configuration
```python
OPENROUTER_API_KEY=your-api-key
DEFAULT_AI_MODEL=claude-3-opus  # or gpt-4, llama, etc.
```

### WebSocket Configuration
```python
WEBSOCKET_SERVER_PORT=8765
CLIENT_HEARTBEAT_INTERVAL=30
```

### User EA Configuration
```python
# Note: Users install PyTrader EA on their own MT5
# Platform provides personalized EA configurations
EA_DOWNLOAD_URL=https://your-platform.com/downloads/ea/{user_id}
```

## 📊 Architecture Overview

```
┌─────────────────────────┐
│   React Frontend        │
└───────────┬─────────────┘
            │
┌───────────▼─────────────┐
│   FastAPI Backend       │
└───────────┬─────────────┘
            │
    ┌───────┴────────┐
    ▼                ▼
┌─────────┐    ┌──────────┐
│   AI    │    │   MT5    │
│ Service │    │Connector │
└─────────┘    └──────────┘
```

## 🎯 How It Works

### For Users:
1. **Register** - Create account on platform
2. **Install MT5** - Install MetaTrader 5 on Windows
3. **Download EA** - Get personalized PyTrader Expert Advisor
4. **Configure EA** - Enter platform credentials
5. **Start Trading** - Receive AI signals automatically

### Technical Flow:
1. Platform generates AI trading signals
2. Signals sent via WebSocket to user's EA
3. PyTrader EA executes trades in user's MT5
4. Trade results sent back to platform
5. Commission calculated on profitable trades

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run frontend tests
cd frontend
npm test
```

## 🚢 Deployment

### Deploy to Render.com
```bash
# Setup Render CLI
npm install -g @render/cli

# Deploy
render deploy
```

### Deploy with Docker
```bash
docker build -t forex-ai-platform .
docker run -p 8000:8000 forex-ai-platform
```

## 📈 API Documentation

### Authentication
```http
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
```

### Trading
```http
GET /api/v1/trading/accounts
POST /api/v1/trading/connect
POST /api/v1/trading/execute
GET /api/v1/trading/positions
```

### Strategies
```http
POST /api/v1/strategies/generate
GET /api/v1/strategies/list
PUT /api/v1/strategies/{id}
DELETE /api/v1/strategies/{id}
```

### Analytics
```http
GET /api/v1/analytics/dashboard
GET /api/v1/analytics/performance
GET /api/v1/analytics/trades
```

## 💰 Commission Structure

- **Volume Commission**: 0.1% per trade
- **Profit Commission**: 10% from profit
- **No hidden fees**
- **Transparent reporting**

## 🔒 Security

- JWT-based authentication
- Data encryption at rest and in transit
- API rate limiting
- Input validation and sanitization
- Regular security audits
- GDPR compliant

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🌐 Resources

- [Documentation](https://docs.forexai.com)
- [API Reference](https://api.forexai.com/docs)
- [Community Forum](https://forum.forexai.com)
- [Discord Server](https://discord.gg/forexai)

## 👥 Team

- **Project Lead**: Your Name
- **Backend Developer**: Backend Dev Name
- **Frontend Developer**: Frontend Dev Name
- **AI Engineer**: AI Dev Name

## 📞 Support

- Email: support@forexai.com
- Discord: [Join our server](https://discord.gg/forexai)
- Documentation: [Read the docs](https://docs.forexai.com)

## ⚠️ Disclaimer

**IMPORTANT**: This software is for educational purposes. Trading forex involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results. Always trade responsibly and never invest money you cannot afford to lose.

**Note**: Users install and run MT5 on their own computers. The platform only generates and transmits trading signals. Users maintain full control of their trading accounts and broker connections.

## 🙏 Acknowledgments

- [Freqtrade](https://github.com/freqtrade/freqtrade) - Trading bot framework
- [PyTrader](https://github.com/TheSnowGuru/PyTrader-python-mt4-mt5-trading-api-connector-drag-n-drop) - MT5 connector
- [OpenRouter](https://openrouter.ai) - LLM API provider

---

Made with ❤️ by the Forex AI Team

**Version**: 1.0.0
**Last Updated**: October 2025

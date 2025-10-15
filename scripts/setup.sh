#!/bin/bash

echo "🚀 Setting up Forex AI Trading Platform..."

# Check if Python 3.11+ is installed
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.11 or higher is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

echo "✅ Docker is installed"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

node_version=$(node --version | grep -Po '(?<=v)\d+')
if [ "$node_version" -lt 18 ]; then
    echo "❌ Node.js 18+ is required. Found: v$node_version"
    exit 1
fi

echo "✅ Node.js version check passed: $(node --version)"

# Create backend virtual environment
echo "📦 Setting up Python virtual environment..."
cd backend
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📥 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create environment file
if [ ! -f .env ]; then
    echo "📝 Creating environment file..."
    cp .env.example .env
    echo "⚠️  Please edit backend/.env with your configuration:"
    echo "   - OPENROUTER_API_KEY: Your OpenRouter API key"
    echo "   - JWT_SECRET: Generate a secure JWT secret"
    echo "   - ENCRYPTION_KEY: Generate a Fernet encryption key"
fi

# Initialize database
echo "🗄️ Initializing database..."
cd ..
docker-compose -f docker-compose.development.yml up -d postgres redis

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 10

# Run database migrations
cd backend
source venv/bin/activate
alembic upgrade head

echo "✅ Database initialized"

# Go back to root directory
cd ..

# Setup frontend
echo "🌐 Setting up frontend..."
cd frontend
npm install

echo "✅ Frontend dependencies installed"

# Create necessary directories
cd ..
mkdir -p backend/ea_packages
mkdir -p logs

echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Edit backend/.env with your API keys and secrets"
echo "2. Run 'docker-compose -f docker-compose.development.yml up' to start all services"
echo "3. Access the API at http://localhost:8000"
echo "4. Access the frontend at http://localhost:3000"
echo "5. View API docs at http://localhost:8000/docs"
echo ""
echo "📚 Documentation:"
echo "- API Documentation: http://localhost:8000/docs"
echo "- Design Document: RANCANGAN_PLATFORM_SAAS_FOREX_AI.md"
echo "- Technical Requirements: TECHNICAL_REQUIREMENTS.md"

#!/bin/bash

echo "🚀 Starting Forex AI Trading Platform..."

# Start services with Docker Compose
if [ "$1" = "dev" ]; then
    echo "🔧 Starting in development mode..."
    docker-compose -f docker-compose.development.yml up
elif [ "$1" = "prod" ]; then
    echo "🏭 Starting in production mode..."
    docker-compose up
else
    echo "🔧 Starting in development mode (default)..."
    docker-compose -f docker-compose.development.yml up
fi

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import sys

from app.core.config import settings
from app.core.database import init_db
from app.api.v1.router import api_router
from app.services.websocket_transmitter import signal_transmitter
from app.services.signal_manager import platform_signal_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("forex_ai_backend.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Forex AI Trading Platform API",
    description="AI-powered forex trading platform with WebSocket signal transmission",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")

# WebSocket endpoint for trading signals
@app.websocket("/ws/trading/{user_id}")
async def trading_websocket(
    websocket: WebSocket,
    user_id: str
):
    """WebSocket endpoint for real-time trading signals"""
    logger.info(f"WebSocket connection attempt for user: {user_id}")
    
    try:
        await signal_transmitter.handle_client_connection(websocket, user_id)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user: {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "forex-ai-backend",
        "version": "1.0.0",
        "timestamp": "2024-01-01T00:00:00Z"
    }

# Startup events
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    try:
        logger.info("Starting Forex AI Trading Platform Backend...")
        
        # Initialize database
        init_db()
        logger.info("Database initialized")
        
        # Start background tasks
        await start_background_tasks()
        
        logger.info("Forex AI Trading Platform Backend started successfully")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Forex AI Trading Platform Backend...")

async def start_background_tasks():
    """Start background tasks for signal processing"""
    import asyncio
    from app.services.signal_manager import platform_signal_manager
    
    # Start signal processing task
    asyncio.create_task(background_signal_processing())
    
    # Start commission processing task
    asyncio.create_task(background_commission_processing())

async def background_signal_processing():
    """Background task for processing market data and generating signals"""
    logger.info("Starting background signal processing...")
    
    while True:
        try:
            # Simulate market data processing
            # In production, this would receive real market data
            await asyncio.sleep(60)  # Process every minute
            
            # Example market data (would come from real data source)
            market_data = {
                'symbol': 'EURUSD',
                'price': 1.0500,
                'timestamp': '2024-01-01T00:00:00Z',
                'volume': 1000,
                'ohlc': {
                    'open': 1.0495,
                    'high': 1.0505,
                    'low': 1.0490,
                    'close': 1.0500
                }
            }
            
            # Process market data and generate signals
            await platform_signal_manager.process_market_data(market_data)
            
        except Exception as e:
            logger.error(f"Error in background signal processing: {e}")
            await asyncio.sleep(10)  # Wait before retrying

async def background_commission_processing():
    """Background task for processing commissions"""
    logger.info("Starting background commission processing...")
    
    while True:
        try:
            # Process commissions every hour
            await asyncio.sleep(3600)  # 1 hour
            
            from app.services.commission_service import commission_settlement
            await commission_settlement.process_daily_commissions()
            
        except Exception as e:
            logger.error(f"Error in background commission processing: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes before retrying

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors"""
    logger.warning(f"Validation error: {exc}")
    return {
        "error": "Validation error",
        "details": exc.errors(),
        "status": 400
    }

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP error {exc.status_code}: {exc.detail}")
    return {
        "error": exc.detail,
        "status": exc.status_code
    }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return {
        "error": "Internal server error",
        "status": 500
    }

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )

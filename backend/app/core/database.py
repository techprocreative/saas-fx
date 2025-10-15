"""
Database Configuration with Optimized Connection Pooling
Implements Phase 1.4 of Production Roadmap
"""
from sqlalchemy import create_engine, event, exc, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
import logging
import time

from .config import settings

logger = logging.getLogger(__name__)

# Create database engine with optimized connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    # Connection Pool Settings
    poolclass=QueuePool,
    pool_size=20,  # Number of connections to maintain
    max_overflow=10,  # Allow up to 30 total connections (20 + 10)
    pool_pre_ping=True,  # Test connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_timeout=30,  # Timeout for getting connection from pool
    
    # Query Settings
    echo=settings.DEBUG,  # Log SQL queries in debug mode
    echo_pool=settings.DEBUG,  # Log pool checkouts in debug mode
    
    # Connection Settings
    connect_args={
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000"  # 30s query timeout
    }
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Prevent unnecessary queries
)

# Create base class for models
Base = declarative_base()


# Event listeners for connection pool monitoring
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log when new connection is created"""
    logger.debug("Database connection established")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log when connection is checked out from pool"""
    logger.debug("Connection checked out from pool")


@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Log when connection is returned to pool"""
    logger.debug("Connection returned to pool")


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    except exc.SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database session
    
    Usage:
        with get_db_context() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except exc.SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    try:
        logger.info("Initializing database tables...")
        from app.models import Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def check_db_health() -> dict:
    """
    Check database health
    
    Returns:
        dict: Health status with metrics
    """
    start_time = time.time()
    
    try:
        with engine.connect() as conn:
            # Test simple query
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
            
            # Get pool status
            pool = engine.pool
            pool_status = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "timeout": pool.timeout()
            }
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "pool": pool_status,
                "timestamp": time.time()
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }


def get_pool_stats() -> dict:
    """
    Get detailed connection pool statistics
    
    Returns:
        dict: Pool statistics
    """
    pool = engine.pool
    
    return {
        "pool_size": pool.size(),
        "connections_checked_in": pool.checkedin(),
        "connections_checked_out": pool.checkedout(),
        "overflow_connections": pool.overflow(),
        "total_connections": pool.size() + pool.overflow(),
        "max_overflow": 10,
        "pool_timeout": pool.timeout()
    }


async def close_db_connections():
    """
    Close all database connections
    Used during application shutdown
    """
    try:
        engine.dispose()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")
        raise

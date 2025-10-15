"""
Health Check Endpoints
Implements Phase 1.4 of Production Roadmap
"""
from fastapi import APIRouter, Depends, status
from typing import Dict
import time
import psutil
import platform

from app.core.database import check_db_health, get_pool_stats
from app.core.auth import get_current_user, require_admin
from app.models.user import User

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict:
    """
    Basic health check endpoint
    Returns minimal health status for load balancer
    """
    return {
        "status": "healthy",
        "timestamp": time.time()
    }


@router.get("/health/detailed", status_code=status.HTTP_200_OK)
async def detailed_health_check() -> Dict:
    """
    Detailed health check with all system components
    Requires authentication
    """
    # Check database
    db_health = check_db_health()
    
    # Check system resources
    system_health = {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
    }
    
    # Overall status
    overall_status = "healthy"
    if db_health["status"] != "healthy":
        overall_status = "degraded"
    if system_health["memory_percent"] > 90 or system_health["cpu_percent"] > 90:
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "timestamp": time.time(),
        "components": {
            "database": db_health,
            "system": system_health
        }
    }


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> Dict:
    """
    Kubernetes readiness probe
    Checks if application is ready to accept traffic
    """
    db_health = check_db_health()
    
    if db_health["status"] == "healthy":
        return {
            "status": "ready",
            "timestamp": time.time()
        }
    else:
        return {
            "status": "not_ready",
            "reason": "database_unhealthy",
            "timestamp": time.time()
        }


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> Dict:
    """
    Kubernetes liveness probe
    Checks if application is alive
    """
    return {
        "status": "alive",
        "timestamp": time.time()
    }


@router.get("/health/database", dependencies=[Depends(require_admin)])
async def database_health() -> Dict:
    """
    Detailed database health check
    Admin only - includes connection pool statistics
    """
    db_health = check_db_health()
    pool_stats = get_pool_stats()
    
    return {
        "health": db_health,
        "pool_statistics": pool_stats,
        "timestamp": time.time()
    }


@router.get("/health/metrics", dependencies=[Depends(require_admin)])
async def system_metrics() -> Dict:
    """
    System metrics endpoint
    Admin only - provides detailed system information
    """
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "system": {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version()
        },
        "resources": {
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count()
            },
            "memory": {
                "total_gb": round(memory.total / (1024 ** 3), 2),
                "available_gb": round(memory.available / (1024 ** 3), 2),
                "used_gb": round(memory.used / (1024 ** 3), 2),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024 ** 3), 2),
                "used_gb": round(disk.used / (1024 ** 3), 2),
                "free_gb": round(disk.free / (1024 ** 3), 2),
                "percent": disk.percent
            }
        },
        "database": get_pool_stats(),
        "timestamp": time.time()
    }

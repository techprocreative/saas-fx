"""
Complete Authentication System with RBAC
Implements Phase 1.2 of Production Roadmap
"""
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import logging

from .security import verify_token, create_access_token, create_refresh_token
from .database import get_db
from ..models.user import User, UserStatus

logger = logging.getLogger(__name__)

security = HTTPBearer()


class Role:
    """User roles for RBAC"""
    ADMIN = "admin"
    USER = "user"
    TRADER = "trader"
    ANALYST = "analyst"
    VIEWER = "viewer"


class Permission:
    """Permissions for different roles"""
    # Trading permissions
    EXECUTE_TRADES = "execute_trades"
    VIEW_TRADES = "view_trades"
    MANAGE_STRATEGIES = "manage_strategies"
    
    # Admin permissions
    MANAGE_USERS = "manage_users"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_SYSTEM = "manage_system"
    
    # User permissions
    MANAGE_PROFILE = "manage_profile"
    VIEW_DASHBOARD = "view_dashboard"


# Role-Permission mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: [
        Permission.EXECUTE_TRADES,
        Permission.VIEW_TRADES,
        Permission.MANAGE_STRATEGIES,
        Permission.MANAGE_USERS,
        Permission.VIEW_ANALYTICS,
        Permission.MANAGE_SYSTEM,
        Permission.MANAGE_PROFILE,
        Permission.VIEW_DASHBOARD,
    ],
    Role.TRADER: [
        Permission.EXECUTE_TRADES,
        Permission.VIEW_TRADES,
        Permission.MANAGE_STRATEGIES,
        Permission.MANAGE_PROFILE,
        Permission.VIEW_DASHBOARD,
    ],
    Role.ANALYST: [
        Permission.VIEW_TRADES,
        Permission.VIEW_ANALYTICS,
        Permission.VIEW_DASHBOARD,
    ],
    Role.USER: [
        Permission.MANAGE_PROFILE,
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_TRADES,
    ],
    Role.VIEWER: [
        Permission.VIEW_DASHBOARD,
    ],
}


class TokenData:
    """Token data structure"""
    def __init__(self, user_id: str, username: str, role: str = Role.USER):
        self.user_id = user_id
        self.username = username
        self.role = role
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        role_perms = ROLE_PERMISSIONS.get(self.role, [])
        return permission in role_perms
    
    def has_any_permission(self, permissions: List[str]) -> bool:
        """Check if user has any of the specified permissions"""
        return any(self.has_permission(perm) for perm in permissions)
    
    def has_all_permissions(self, permissions: List[str]) -> bool:
        """Check if user has all specified permissions"""
        return all(self.has_permission(perm) for perm in permissions)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = verify_token(token, token_type="access")
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise credentials_exception
        
        # Check if user is active
        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not active"
            )
        
        logger.info(f"User authenticated: {user.username} (ID: {user.id})")
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user (additional check)"""
    if current_user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


class RoleChecker:
    """Dependency for checking user roles"""
    
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles
    
    async def __call__(self, user: User = Depends(get_current_user)) -> User:
        # Get user role from user attributes or default to USER
        user_role = getattr(user, 'role', Role.USER)
        
        if user_role not in self.allowed_roles:
            logger.warning(
                f"Access denied for user {user.username} (role: {user_role}) "
                f"- requires roles: {self.allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user


class PermissionChecker:
    """Dependency for checking user permissions"""
    
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions
    
    async def __call__(self, user: User = Depends(get_current_user)) -> User:
        user_role = getattr(user, 'role', Role.USER)
        user_permissions = ROLE_PERMISSIONS.get(user_role, [])
        
        # Check if user has all required permissions
        if not all(perm in user_permissions for perm in self.required_permissions):
            logger.warning(
                f"Permission denied for user {user.username} (role: {user_role}) "
                f"- requires permissions: {self.required_permissions}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user


# Convenience dependencies for common role checks
require_admin = RoleChecker([Role.ADMIN])
require_trader = RoleChecker([Role.ADMIN, Role.TRADER])
require_analyst = RoleChecker([Role.ADMIN, Role.ANALYST])


# Convenience dependencies for common permission checks
require_trade_execution = PermissionChecker([Permission.EXECUTE_TRADES])
require_user_management = PermissionChecker([Permission.MANAGE_USERS])
require_system_management = PermissionChecker([Permission.MANAGE_SYSTEM])


class RefreshTokenManager:
    """Manage refresh tokens with Redis for revocation"""
    
    def __init__(self):
        self.redis_client = None  # Will be initialized with Redis connection
    
    async def store_refresh_token(self, user_id: str, token: str, expires_in: int):
        """Store refresh token in Redis"""
        if self.redis_client:
            key = f"refresh_token:{user_id}:{token[-8:]}"
            await self.redis_client.setex(key, expires_in, token)
    
    async def revoke_refresh_token(self, user_id: str, token: str):
        """Revoke a refresh token"""
        if self.redis_client:
            key = f"refresh_token:{user_id}:{token[-8:]}"
            await self.redis_client.delete(key)
    
    async def is_token_revoked(self, user_id: str, token: str) -> bool:
        """Check if refresh token is revoked"""
        if self.redis_client:
            key = f"refresh_token:{user_id}:{token[-8:]}"
            exists = await self.redis_client.exists(key)
            return not exists
        return False


refresh_token_manager = RefreshTokenManager()


def create_tokens(user_id: str, username: str, role: str = Role.USER):
    """Create both access and refresh tokens"""
    
    token_data = {
        "sub": str(user_id),
        "username": username,
        "role": role,
    }
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


async def refresh_access_token(
    refresh_token: str,
    db: Session = Depends(get_db)
) -> dict:
    """Generate new access token from refresh token"""
    
    try:
        # Verify refresh token
        payload = verify_token(refresh_token, token_type="refresh")
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check if token is revoked
        if await refresh_token_manager.is_token_revoked(user_id, refresh_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked"
            )
        
        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if user is None or user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new access token
        user_role = getattr(user, 'role', Role.USER)
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "role": user_role,
        }
        
        new_access_token = create_access_token(token_data)
        
        logger.info(f"Access token refreshed for user: {user.username}")
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token"
        )


async def logout_user(
    user_id: str,
    refresh_token: str
):
    """Logout user by revoking refresh token"""
    try:
        await refresh_token_manager.revoke_refresh_token(user_id, refresh_token)
        logger.info(f"User logged out: {user_id}")
        return {"message": "Successfully logged out"}
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

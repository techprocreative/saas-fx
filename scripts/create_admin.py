#!/usr/bin/env python3
"""
Script to create initial admin user for development
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.core.database import get_db, init_db
from app.models import User, UserStatus
from app.core.security import hash_password
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_admin_user():
    """Create initial admin user"""
    
    # Get database session
    db = next(get_db())
    
    try:
        # Check if admin user already exists
        existing_admin = db.query(User).filter(
            User.email == "admin@forexai.com"
        ).first()
        
        if existing_admin:
            logger.info("Admin user already exists")
            logger.info(f"Email: {existing_admin.email}")
            logger.info(f"Username: {existing_admin.username}")
            return
        
        # Create admin user
        admin_user = User(
            email="admin@forexai.com",
            username="admin",
            password_hash=hash_password("admin123"),
            status=UserStatus.ACTIVE
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        logger.info("✅ Admin user created successfully")
        logger.info(f"Email: {admin_user.email}")
        logger.info(f"Username: {admin_user.username}")
        logger.info("Password: admin123")
        logger.info("⚠️  Please change the password after first login!")
        
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Creating admin user...")
    
    # Initialize database first
    try:
        init_db()
        create_admin_user()
        logger.info("Setup completed successfully!")
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)

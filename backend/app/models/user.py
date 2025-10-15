from sqlalchemy import Column, String, Enum
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class UserStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class User(BaseModel):
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    
    # Relationships
    trading_accounts = relationship("TradingAccount", back_populates="user")
    ai_strategies = relationship("AIStrategy", back_populates="user")
    commissions = relationship("Commission", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"

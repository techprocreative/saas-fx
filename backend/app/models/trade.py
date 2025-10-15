from sqlalchemy import Column, String, Integer, DECIMAL, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum

class ConnectionStatus(enum.Enum):
    OFFLINE = "offline"
    ONLINE = "online"
    CONNECTING = "connecting"
    ERROR = "error"

class OrderType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class TradeStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class TradingAccount(BaseModel):
    __tablename__ = "trading_accounts"
    
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    mt5_login = Column(String(50), nullable=False)
    broker = Column(String(100), nullable=False)
    account_type = Column(String(50))
    balance = Column(DECIMAL(20, 2), default=0.0)
    
    # Connection tracking
    connection_status = Column(Enum(ConnectionStatus), default=ConnectionStatus.OFFLINE)
    websocket_connection_id = Column(String(100))
    pytrader_ea_version = Column(String(20))
    last_ping = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="trading_accounts")
    trades = relationship("Trade", back_populates="account")
    
    def __repr__(self):
        return f"<TradingAccount(id={self.id}, mt5_login={self.mt5_login}, broker={self.broker})>"

class AIStrategy(BaseModel):
    __tablename__ = "ai_strategies"
    
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    llm_model = Column(String(100))
    strategy_config = Column(Text)  # JSON string
    performance_metrics = Column(Text)  # JSON string
    status = Column(String(50), default="active")
    
    # Relationships
    user = relationship("User", back_populates="ai_strategies")
    trades = relationship("Trade", back_populates="strategy")
    
    def __repr__(self):
        return f"<AIStrategy(id={self.id}, name={self.name}, llm_model={self.llm_model})>"

class Trade(BaseModel):
    __tablename__ = "trades"
    
    account_id = Column(PG_UUID(as_uuid=True), ForeignKey("trading_accounts.id"), nullable=False)
    strategy_id = Column(PG_UUID(as_uuid=True), ForeignKey("ai_strategies.id"))
    
    symbol = Column(String(20), nullable=False)
    type = Column(Enum(OrderType), nullable=False)
    volume = Column(DECIMAL(10, 2), nullable=False)
    open_price = Column(DECIMAL(10, 5), nullable=False)
    close_price = Column(DECIMAL(10, 5))
    stop_loss = Column(DECIMAL(10, 5))
    take_profit = Column(DECIMAL(10, 5))
    profit_loss = Column(DECIMAL(10, 2), default=0.0)
    commission = Column(DECIMAL(10, 2), default=0.0)
    status = Column(Enum(TradeStatus), default=TradeStatus.OPEN)
    
    # MT5 specific fields
    mt5_order_id = Column(String(50))  # Order ID from MT5
    mt5_position_id = Column(String(50))  # Position ID from MT5
    
    opened_at = Column(DateTime(timezone=True), nullable=False)
    closed_at = Column(DateTime(timezone=True))
    
    # Relationships
    account = relationship("TradingAccount", back_populates="trades")
    strategy = relationship("AIStrategy", back_populates="trades")
    commissions = relationship("Commission", back_populates="trade")
    
    def __repr__(self):
        return f"<Trade(id={self.id}, symbol={self.symbol}, type={self.type}, volume={self.volume})>"

class Commission(BaseModel):
    __tablename__ = "commissions"
    
    trade_id = Column(PG_UUID(as_uuid=True), ForeignKey("trades.id"), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    status = Column(String(50), default="pending")
    processed_at = Column(DateTime(timezone=True))
    
    # Commission breakdown
    volume_commission = Column(DECIMAL(10, 2), default=0.0)
    profit_commission = Column(DECIMAL(10, 2), default=0.0)
    
    # Relationships
    trade = relationship("Trade", back_populates="commissions")
    user = relationship("User", back_populates="commissions")
    
    def __repr__(self):
        return f"<Commission(id={self.id}, amount={self.amount}, status={self.status})>"

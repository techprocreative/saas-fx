import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, User, TradingAccount, AIStrategy, Trade, Commission
from app.core.security import hash_password

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(
        email="test@example.com",
        username="testuser",
        password_hash=hash_password("testpassword123")
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def test_trading_account(db_session, test_user):
    """Create a test trading account"""
    account = TradingAccount(
        user_id=test_user.id,
        mt5_login="123456789",
        broker="TestBroker",
        balance=10000.0
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account

@pytest.fixture
def test_ai_strategy(db_session, test_user):
    """Create a test AI strategy"""
    strategy = AIStrategy(
        user_id=test_user.id,
        name="Test Strategy",
        llm_model="claude-3-opus",
        strategy_config='{"test": "config"}',
        status="active"
    )
    db_session.add(strategy)
    db_session.commit()
    db_session.refresh(strategy)
    return strategy

class TestUserModel:
    """Test User model"""
    
    def test_create_user(self, db_session):
        """Test user creation"""
        user = User(
            email="newuser@example.com",
            username="newuser",
            password_hash=hash_password("password123")
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.username == "newuser"
        assert user.status.value == "active"
    
    def test_user_repr(self, test_user):
        """Test user string representation"""
        repr_str = repr(test_user)
        assert "User" in repr_str
        assert test_user.username in repr_str
        assert test_user.email in repr_str

class TestTradingAccountModel:
    """Test TradingAccount model"""
    
    def test_create_trading_account(self, db_session, test_user):
        """Test trading account creation"""
        account = TradingAccount(
            user_id=test_user.id,
            mt5_login="987654321",
            broker="AnotherBroker",
            balance=5000.0
        )
        db_session.add(account)
        db_session.commit()
        
        assert account.id is not None
        assert account.mt5_login == "987654321"
        assert account.broker == "AnotherBroker"
        assert float(account.balance) == 5000.0
        assert account.user_id == test_user.id
    
    def test_account_user_relationship(self, test_trading_account, test_user):
        """Test account-user relationship"""
        assert test_trading_account.user.id == test_user.id
        assert test_trading_account.user.email == test_user.email

class TestAIStrategyModel:
    """Test AIStrategy model"""
    
    def test_create_ai_strategy(self, db_session, test_user):
        """Test AI strategy creation"""
        strategy = AIStrategy(
            user_id=test_user.id,
            name="New Strategy",
            llm_model="gpt-4",
            strategy_config='{"indicators": ["RSI", "MACD"]}',
            status="active"
        )
        db_session.add(strategy)
        db_session.commit()
        
        assert strategy.id is not None
        assert strategy.name == "New Strategy"
        assert strategy.llm_model == "gpt-4"
        assert strategy.status == "active"
    
    def test_strategy_user_relationship(self, test_ai_strategy, test_user):
        """Test strategy-user relationship"""
        assert test_ai_strategy.user.id == test_user.id
        assert test_ai_strategy.user.email == test_user.email

class TestTradeModel:
    """Test Trade model"""
    
    def test_create_trade(self, db_session, test_trading_account, test_ai_strategy):
        """Test trade creation"""
        trade = Trade(
            account_id=test_trading_account.id,
            strategy_id=test_ai_strategy.id,
            symbol="EURUSD",
            type="BUY",
            volume=0.1,
            open_price=1.0500,
            stop_loss=1.0450,
            take_profit=1.0600
        )
        db_session.add(trade)
        db_session.commit()
        
        assert trade.id is not None
        assert trade.symbol == "EURUSD"
        assert trade.type.value == "BUY"
        assert float(trade.volume) == 0.1
        assert float(trade.open_price) == 1.0500
    
    def test_trade_relationships(self, db_session, test_trading_account, test_ai_strategy):
        """Test trade relationships"""
        trade = Trade(
            account_id=test_trading_account.id,
            strategy_id=test_ai_strategy.id,
            symbol="GBPUSD",
            type="SELL",
            volume=0.2,
            open_price=1.2500
        )
        db_session.add(trade)
        db_session.commit()
        
        assert trade.account.id == test_trading_account.id
        assert trade.strategy.id == test_ai_strategy.id

class TestCommissionModel:
    """Test Commission model"""
    
    def test_create_commission(self, db_session, test_trading_account, test_ai_strategy, test_user):
        """Test commission creation"""
        # First create a trade
        trade = Trade(
            account_id=test_trading_account.id,
            strategy_id=test_ai_strategy.id,
            symbol="EURUSD",
            type="BUY",
            volume=0.1,
            open_price=1.0500,
            close_price=1.0600,
            profit_loss=10.0
        )
        db_session.add(trade)
        db_session.commit()
        
        # Create commission
        commission = Commission(
            trade_id=trade.id,
            user_id=test_user.id,
            amount=1.5,
            volume_commission=1.0,
            profit_commission=0.5
        )
        db_session.add(commission)
        db_session.commit()
        
        assert commission.id is not None
        assert float(commission.amount) == 1.5
        assert commission.trade_id == trade.id
        assert commission.user_id == test_user.id

class TestModelValidation:
    """Test model validation and constraints"""
    
    def test_unique_email_constraint(self, db_session):
        """Test email uniqueness constraint"""
        user1 = User(
            email="same@example.com",
            username="user1",
            password_hash=hash_password("password123")
        )
        user2 = User(
            email="same@example.com",  # Same email
            username="user2",
            password_hash=hash_password("password123")
        )
        
        db_session.add(user1)
        db_session.commit()
        
        db_session.add(user2)
        with pytest.raises(Exception):  # Should raise an integrity error
            db_session.commit()
    
    def test_unique_username_constraint(self, db_session):
        """Test username uniqueness constraint"""
        user1 = User(
            email="user1@example.com",
            username="sameuser",
            password_hash=hash_password("password123")
        )
        user2 = User(
            email="user2@example.com",
            username="sameuser",  # Same username
            password_hash=hash_password("password123")
        )
        
        db_session.add(user1)
        db_session.commit()
        
        db_session.add(user2)
        with pytest.raises(Exception):  # Should raise an integrity error
            db_session.commit()

if __name__ == "__main__":
    pytest.main([__file__])

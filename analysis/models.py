from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date, JSON, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from pathlib import Path

Base = declarative_base()

class Transaction(Base):
    __tablename__ = 'transactions'

    transaction_id = Column(String, primary_key=True)
    account_id = Column(String, index=True)
    date = Column(Date)
    name = Column(String)
    amount = Column(Float)
    currency = Column(String, nullable=True)
    category = Column(JSON, nullable=True) # Storing list of categories as JSON
    category_id = Column(String, nullable=True)
    pending = Column(Boolean)
    merchant_name = Column(String, nullable=True)
    payment_channel = Column(String, nullable=True)
    
    # Store the full raw response to ensure we capture EVERYTHING available
    raw_json = Column(JSON)

    def __repr__(self):
        return f"<Transaction(id='{self.transaction_id}', date='{self.date}', amount={self.amount}, name='{self.name}')>"

class InvestmentHolding(Base):
    __tablename__ = 'investment_holdings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date_captured = Column(Date, index=True) # To snapshot holdings over time
    account_id = Column(String, index=True)
    security_id = Column(String, ForeignKey('securities.security_id'), index=True)
    quantity = Column(Float)
    institution_price = Column(Float)
    institution_value = Column(Float)
    cost_basis = Column(Float, nullable=True)
    currency = Column(String, nullable=True)
    
    # Store full raw response
    raw_json = Column(JSON)

    security = relationship("Security", back_populates="holdings")

    def __repr__(self):
        return f"<InvestmentHolding(date='{self.date_captured}', security_id='{self.security_id}', value={self.institution_value})>"

class Security(Base):
    __tablename__ = 'securities'

    security_id = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    ticker_symbol = Column(String, nullable=True)
    institution_security_id = Column(String, nullable=True)
    type = Column(String, nullable=True)
    close_price = Column(Float, nullable=True)
    close_price_as_of = Column(Date, nullable=True)
    currency = Column(String, nullable=True)
    is_cash_equivalent = Column(Boolean, nullable=True)
    
    # Store full raw response
    raw_json = Column(JSON)

    holdings = relationship("InvestmentHolding", back_populates="security")

    def __repr__(self):
        return f"<Security(name='{self.name}', ticker='{self.ticker_symbol}')>"

# Database Setup
DB_FILE = Path(__file__).parent / 'financial_data_v2.db'
DATABASE_URL = f"sqlite:///{DB_FILE}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

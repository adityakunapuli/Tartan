from sqlalchemy import Column, Integer, String, Float, Boolean, Date, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Transaction(Base):
    __tablename__ = 'transactions'

    transaction_id = Column(String, primary_key=True)
    account_id = Column(String, index=True)
    date = Column(Date)
    name = Column(String)
    amount = Column(Float)
    currency = Column(String, nullable=True)
    category = Column(JSON, nullable=True)
    category_id = Column(String, nullable=True)
    pending = Column(Boolean)
    merchant_name = Column(String, nullable=True)
    payment_channel = Column(String, nullable=True)
    raw_json = Column(JSON)

    def __repr__(self):
        return f"<Transaction(id='{self.transaction_id}', date='{self.date}', amount={self.amount}, name='{self.name}')>"

class InvestmentTransaction(Base):
    __tablename__ = 'investment_transactions'

    investment_transaction_id = Column(String, primary_key=True)
    account_id = Column(String, index=True)
    security_id = Column(String, ForeignKey('securities.security_id'), index=True)
    date = Column(Date)
    name = Column(String)
    quantity = Column(Float)
    amount = Column(Float)
    price = Column(Float)
    fees = Column(Float, nullable=True)
    type = Column(String)
    subtype = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    raw_json = Column(JSON)

    security = relationship("Security")

    def __repr__(self):
        return f"<InvestmentTransaction(id='{self.investment_transaction_id}', date='{self.date}', type='{self.type}', amount={self.amount})>"

class InvestmentHolding(Base):
    __tablename__ = 'investment_holdings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date_captured = Column(Date, index=True)
    account_id = Column(String, index=True)
    security_id = Column(String, ForeignKey('securities.security_id'), index=True)
    quantity = Column(Float)
    institution_price = Column(Float)
    institution_value = Column(Float)
    cost_basis = Column(Float, nullable=True)
    currency = Column(String, nullable=True)
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
    raw_json = Column(JSON)

    holdings = relationship("InvestmentHolding", back_populates="security")

    def __repr__(self):
        return f"<Security(name='{self.name}', ticker='{self.ticker_symbol}')>"

class CategoryRule(Base):
    __tablename__ = 'category_rules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # The key to match against. 
    # If merchant_name exists in transaction, we match against 'merchant_name'.
    # If not, we match against 'name'.
    match_value = Column(String, unique=True, index=True) 
    match_type = Column(String) # 'merchant_name' or 'name'
    category = Column(String) # The standardized category (e.g. "Groceries")
    
    def __repr__(self):
        return f"<CategoryRule(match='{self.match_value}', category='{self.category}')>"

"""Database models for financial data."""

from sqlalchemy import Column, Integer, String, Float, Boolean, Date, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Transaction(Base):
    """SQLAlchemy model for bank transactions.

    Attributes:
        transaction_id (str): Unique identifier from Plaid.
        account_id (str): Reference to the account.
        date (date): Transaction date.
        name (str): Raw transaction name.
        amount (float): Transaction amount.
        currency (str): ISO currency code.
        category (dict): Plaid categories (JSON).
        category_id (str): Plaid category ID.
        pending (bool): Whether the transaction is pending.
        merchant_name (str): Cleaned merchant name from Plaid.
        payment_channel (str): Method of payment (e.g., 'in store').
        raw_json (dict): Full raw JSON from Plaid.
    """
    __tablename__ = 'transactions'

    transaction_id = Column(String, primary_key=True)
    account_id = Column(String, index=True)
    date = Column(Date)
    name = Column(String)
    amount = Column(Float)
    currency = Column(String, nullable=True)
    flow_type = Column(String, nullable=True)  # 'INCOME', 'EXPENSE', 'TRANSFER'
    category = Column(JSON, nullable=True)
    category_id = Column(String, nullable=True)
    pending = Column(Boolean)
    merchant_name = Column(String, nullable=True)
    payment_channel = Column(String, nullable=True)
    raw_json = Column(JSON)

    def __repr__(self):
        return f"<Transaction(id='{self.transaction_id}', date='{self.date}', amount={self.amount}, name='{self.name}')>"

class InvestmentTransaction(Base):
    """SQLAlchemy model for investment transactions.

    Attributes:
        investment_transaction_id (str): Unique identifier from Plaid.
        account_id (str): Reference to the account.
        security_id (str): Reference to the security.
        date (date): Transaction date.
        name (str): Transaction description.
        quantity (float): Number of units.
        amount (float): Total value of transaction.
        price (float): Price per unit.
        fees (float): Transaction fees.
        type (str): Transaction type (e.g., 'buy', 'sell').
        subtype (str): Detailed transaction type.
        currency (str): ISO currency code.
        raw_json (dict): Full raw JSON from Plaid.
    """
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
    """SQLAlchemy model for investment holdings (positions).

    Attributes:
        id (int): Internal primary key.
        date_captured (date): Date the holding was recorded.
        account_id (str): Reference to the account.
        security_id (str): Reference to the security.
        quantity (float): Number of units held.
        institution_price (float): Price per unit from institution.
        institution_value (float): Total value held.
        cost_basis (float): Total cost of position.
        currency (str): ISO currency code.
        raw_json (dict): Full raw JSON from Plaid.
    """
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
    """SQLAlchemy model for securities (stocks, funds, etc.).

    Attributes:
        security_id (str): Unique identifier from Plaid.
        name (str): Full name of the security.
        ticker_symbol (str): Ticker symbol.
        institution_security_id (str): ID from the financial institution.
        type (str): Type (e.g., 'equity', 'mutual fund').
        close_price (float): Last known closing price.
        close_price_as_of (date): Date of the closing price.
        currency (str): ISO currency code.
        is_cash_equivalent (bool): Whether it is a cash-like asset.
        raw_json (dict): Full raw JSON from Plaid.
    """
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

class Account(Base):
    """SQLAlchemy model for financial accounts.

    Attributes:
        account_id (str): Unique identifier from Plaid.
        name (str): Account name.
        mask (str): Last 4 digits.
        type (str): Account type (e.g., 'depository').
        subtype (str): Account subtype (e.g., 'checking').
        current_balance (float): Current balance.
        available_balance (float): Available balance.
        iso_currency_code (str): ISO currency code.
        limit (float): Credit limit.
        apy (float): Annual Percentage Yield.
        interest_rate (float): Interest rate.
        maturity_date (date): Maturity date for CDs/Loans.
        last_updated (date): Date of last sync.
        raw_json (dict): Full raw JSON from Plaid.
    """
    __tablename__ = 'accounts'

    account_id = Column(String, primary_key=True)
    name = Column(String)
    mask = Column(String, nullable=True)
    type = Column(String)
    subtype = Column(String, nullable=True)
    current_balance = Column(Float, nullable=True)
    available_balance = Column(Float, nullable=True)
    iso_currency_code = Column(String, nullable=True)
    limit = Column(Float, nullable=True)
    apy = Column(Float, nullable=True)
    interest_rate = Column(Float, nullable=True)
    maturity_date = Column(Date, nullable=True)
    last_updated = Column(Date)
    raw_json = Column(JSON)

    def __repr__(self):
        return f"<Account(name='{self.name}', type='{self.type}', balance={self.current_balance})>"

class CategoryRule(Base):
    """SQLAlchemy model for transaction categorization rules.

    Attributes:
        id (int): Internal primary key.
        match_value (str): The merchant name or pattern to match.
        match_type (str): Either 'merchant_name' or 'pattern'.
        category (str): The assigned category.
    """
    __tablename__ = 'category_rules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # The key to match against. 
    # If merchant_name exists in transaction, we match against 'merchant_name'.
    # If not, we match against 'name'.
    match_value = Column(String, unique=True, index=True) 
    match_type = Column(String) # 'merchant_name' or 'name'
    flow_type = Column(String) # 'INCOME', 'EXPENSE', 'TRANSFER'
    category = Column(String) # The standardized category (e.g. "Groceries")
    
    def __repr__(self):
        return f"<CategoryRule(match='{self.match_value}', category='{self.category}', flow='{self.flow_type}')>"


"""SQLModel definition for category rules."""

from sqlmodel import Field, SQLModel


class CategoryRule(SQLModel, table=True):
    """Represents a rule for categorizing transactions based on merchant/name matching."""
    __tablename__ = "category_rules"

    id: int | None = Field(default=None, primary_key=True)
    match_value: str = Field(unique=True, index=True)
    match_type: str  # 'merchant_name' or 'name'
    flow_type: str  # 'INCOME', 'EXPENSE', 'TRANSFER'
    category: str

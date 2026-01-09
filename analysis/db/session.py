from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

# Path relative to the project root
DB_PATH = "sqlite:///analysis/financial_data.db"

engine = create_engine(DB_PATH)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

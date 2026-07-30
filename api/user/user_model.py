from sqlalchemy import (
    Column,
    String,
    Integer
)

from api.db.pg_database import Base

class Users(Base):
    """
    This is the schema for user details
    """
    __tablename__ = "users"
    id = Column(String(255), primary_key=True)
    email = Column(String(255), nullable=False, unique=True)
    codeforces_handle = Column(String(255), nullable=True, unique=True)
    contest_rating = Column(Integer, nullable=True)
    max_contest_rating = Column(Integer, nullable=True)
    best_performance = Column(Integer, nullable=True)
    contest_attempts = Column(Integer, nullable=False)
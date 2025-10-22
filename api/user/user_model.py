from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    UUID
)
from uuid import uuid4
from api.db.pg_database import Base

from datetime import datetime, timezone

class User(Base):
    
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    codeforces_handle = Column(String(255))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
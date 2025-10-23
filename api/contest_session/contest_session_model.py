from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    UUID,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import expression
from sqlalchemy import (
    Column
)
from uuid import uuid4
from api.db.pg_database import Base

from datetime import datetime,timezone

class ContestSession(Base):

    __tablename__ = "contest_session"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    contest_level = Column(Integer, nullable=False)
    contest_theme = Column(String, nullable=False)
    start_time = Column(String, nullable=True)
    end_time = Column(String, nullable=True)
    duration = Column(Integer, nullable=False)
    rating_1 = Column(Integer, nullable=False)
    rating_2 = Column(Integer, nullable=False)
    rating_3 = Column(Integer, nullable=False)
    rating_4 = Column(Integer, nullable=False)
    t1 = Column(String, nullable=True)
    t2 = Column(String, nullable=True)
    t3 = Column(String, nullable=True)
    t4 = Column(String, nullable=True)
    problem_1_id = Column(String, nullable=False)
    problem_2_id = Column(String, nullable=False)
    problem_3_id = Column(String, nullable=False)
    problem_4_id = Column(String, nullable=False)
    problem_1_index = Column(String, nullable=False)
    problem_2_index = Column(String, nullable=False)
    problem_3_index = Column(String, nullable=False)
    problem_4_index = Column(String, nullable=False)
    status = Column(String, nullable=False, default="review")
    problem_listed = Column(JSONB, server_default=expression.text("'[]'::jsonb"), nullable=False)
    date = Column(DateTime, nullable=True)



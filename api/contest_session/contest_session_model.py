from fastapi.datastructures import Default
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    UUID,
    ForeignKey,
    JSONB
)
from uuid import uuid4
from api.db.pg_database import Base

from datetime import datetime,timezone

class ContestSession(Base):

    __tablename__ = "contest_session"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), ForeignKey("user.id"), nullable=False)
    contest_level = Column(Integer, nullable=False)
    contest_theme = Column(String, nullable=False)
    start_time = Column(String, nullable=True)
    end_time = Column(String, nullable=True)
    duration = Column(Integer, nullable=False)
    rating_1 = Column(Integer, nullable=False)
    rating_2 = Column(Integer, nullable=False)
    rating_3 = Column(Integer, nullable=False)
    rating_4 = Column(Integer, nullable=False)
    t1 = Column(String, Default=None, nullable=True)
    t2 = Column(String, Default=None, nullable=True)
    t3 = Column(String, Default=None, nullable=True)
    t4 = Column(String, Default=None, nullable=True)
    problem_1_id = Column(String, nullable=False)
    problem_2_id = Column(String, nullable=False)
    problem_3_id = Column(String, nullable=False)
    problem_4_id = Column(String, nullable=False)
    problem_1_index = Column(String, nullable=False)
    problem_2_index = Column(String, nullable=False)
    problem_3_index = Column(String, nullable=False)
    problem_4_index = Column(String, nullable=False)
    status = Column(String, Default="review", nullable=False)
    problem_listed = Column(JSONB, default=[])
    date = Column(DateTime, default=None, nullable=True)



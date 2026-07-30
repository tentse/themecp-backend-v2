from sqlalchemy import Column, Integer
from api.db.pg_database import Base


class ContestLevel(Base):
    """
    This is the schema for contest levels
    """
    __tablename__ = "contest_levels"
    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(Integer, unique=True, nullable=False)
    duration_in_min = Column(Integer, nullable=False)
    performance = Column(Integer, nullable=False)
    p1_rating = Column(Integer, nullable=False)
    p2_rating = Column(Integer, nullable=False)
    p3_rating = Column(Integer, nullable=False)
    p4_rating = Column(Integer, nullable=False)
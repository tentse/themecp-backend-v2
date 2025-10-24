from sqlalchemy import (
    Integer,
    Column
)

from api.db.pg_database import Base

class ContestLevel(Base):

    __tablename__ = "contest_level"

    level = Column(Integer, primary_key=True, nullable=False)
    duration = Column(Integer, nullable=False)
    performance = Column(Integer, nullable=False)
    rating_1 = Column(Integer, nullable=False)
    rating_2 = Column(Integer, nullable=False)
    rating_3 = Column(Integer, nullable=False)
    rating_4 = Column(Integer, nullable=False)
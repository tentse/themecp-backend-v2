from sqlalchemy import Column, String, Integer
from api.db.pg_database import Base


class ContestThemes(Base):
    """
    This is a schema for contest themes
    """
    __tablename__ = "contest_theme"
    id = Column(Integer, primary_key=True, autoincrement=True)
    theme = Column(String(255), nullable=False, unique=True)
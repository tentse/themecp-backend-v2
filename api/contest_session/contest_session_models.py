from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    ForeignKey,
    PrimaryKeyConstraint
)
from api.db.pg_database import Base

CONTEST_SESSION_ID = "contest_session.id"

class ContestSession(Base):
    """
    This is the schema for user contest session
    """
    __tablename__ = "contest_session"
    id = Column(String(255), primary_key=True)
    user_id = Column(String(255), nullable=False)
    level = Column(Integer, nullable=False)
    theme = Column(String(255), nullable=False)
    duration_in_min = Column(Integer, nullable=False)
    status = Column(String(255), nullable=False)
    starts_at = Column(BigInteger, nullable=True)
    ends_at = Column(BigInteger, nullable=True)
    p1_cf_contestId = Column("p1_cf_contestID", String(255), nullable=False)
    p1_cf_index = Column(String(255), nullable=False)
    p2_cf_contestId = Column("p2_cf_contestID", String(255), nullable=False)
    p2_cf_index = Column(String(255), nullable=False)
    p3_cf_contestId = Column("p3_cf_contestID", String(255), nullable=False)
    p3_cf_index = Column(String(255), nullable=False)
    p4_cf_contestId = Column("p4_cf_contestID", String(255), nullable=False)
    p4_cf_index = Column(String(255), nullable=False)


class ContestSessionSeenProblem(Base):
    """
    This is the schema for keeping track of which problem
    user have seen while generating contest
    """
    __tablename__ = "contest_session_seen_problem"
    __table_args__ = (
        PrimaryKeyConstraint(
            'session_id',
            'cf_problem_contestID',
            'cf_problem_index'
        ),
    )
    session_id = Column(
        String(255),
        ForeignKey(CONTEST_SESSION_ID, ondelete='CASCADE'),
        nullable=False
    )
    cf_problem_contestId = Column("cf_problem_contestID", String(255), nullable=False)
    cf_problem_index = Column(String(255), nullable=False)


class ContestSessionProblemsStatus(Base):
    """
    This schema is for tracking problem status whether it's been solved
    or not and at what time this problem is solved at
    """
    __tablename__ = "contest_session_problems_status"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(255),
        ForeignKey(CONTEST_SESSION_ID, ondelete='CASCADE'),
        nullable=False
    )
    problem_number = Column(Integer, nullable=False)
    problem_contestId = Column("problem_contestID", String(255), nullable=False)
    problem_index = Column(String(255), nullable=False)
    problem_rating = Column(Integer, nullable=False)
    status = Column(String(255), nullable=False)
    accepted_at = Column(String(255), nullable=True)
    solved_in_min = Column(Integer, nullable=True)


class ContestSessionResult(Base):
    """
    This schema is for keeping track of contest session resulted such as 
    performance, rating
    """
    __tablename__ = "contest_session_result"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(255),
        ForeignKey(CONTEST_SESSION_ID, ondelete='CASCADE'),
        nullable=False
    )
    solved_count = Column(Integer, nullable=False)
    performance = Column(Integer, nullable=False)
    rating_before = Column(Integer, nullable=False)
    rating_after = Column(Integer, nullable=False)
    rating_delta = Column(Integer, nullable=False)

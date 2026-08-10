from dataclasses import dataclass

from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    ForeignKey,
    Index,
    PrimaryKeyConstraint
)
from api.db.pg_database import Base
from .contest_session_response_models import ProblemStatus

CONTEST_SESSION_ID = "contest_session.id"


@dataclass
class ProblemSlot:
    """
    A read/write view of one of the four problem slots on a ContestSession.

    Mirrors the shape of the rows that contest_session_problems_status used to
    return, so performance calculation and status mapping keep working against
    the merged table without change. Deliberately not frozen: the refresh flow
    mutates these in place so the response reflects newly solved problems.
    """
    problem_number: int
    problem_contestId: str
    problem_index: str
    problem_rating: int | None
    status: str
    accepted_at: int | None
    solved_in_min: int | None


class ContestSession(Base):
    """
    This is the schema for user contest session.

    Holds the whole lifecycle of a session in one row: configuration set at
    REVIEW, the four problems and their ratings/statuses set at RUNNING, and the
    outcome set at FINISHED. Columns written after REVIEW are nullable because
    the row exists before those stages are reached.
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
    p1_rating = Column(Integer, nullable=True)
    p1_status = Column(String(255), nullable=True)
    p1_accepted_at = Column(BigInteger, nullable=True)
    p1_solved_in_min = Column(Integer, nullable=True)

    p2_cf_contestId = Column("p2_cf_contestID", String(255), nullable=False)
    p2_cf_index = Column(String(255), nullable=False)
    p2_rating = Column(Integer, nullable=True)
    p2_status = Column(String(255), nullable=True)
    p2_accepted_at = Column(BigInteger, nullable=True)
    p2_solved_in_min = Column(Integer, nullable=True)

    p3_cf_contestId = Column("p3_cf_contestID", String(255), nullable=False)
    p3_cf_index = Column(String(255), nullable=False)
    p3_rating = Column(Integer, nullable=True)
    p3_status = Column(String(255), nullable=True)
    p3_accepted_at = Column(BigInteger, nullable=True)
    p3_solved_in_min = Column(Integer, nullable=True)

    p4_cf_contestId = Column("p4_cf_contestID", String(255), nullable=False)
    p4_cf_index = Column(String(255), nullable=False)
    p4_rating = Column(Integer, nullable=True)
    p4_status = Column(String(255), nullable=True)
    p4_accepted_at = Column(BigInteger, nullable=True)
    p4_solved_in_min = Column(Integer, nullable=True)

    performance = Column(Integer, nullable=True)
    rating_before = Column(Integer, nullable=True)
    rating_after = Column(Integer, nullable=True)
    rating_delta = Column(Integer, nullable=True)

    # Declared here, not only in a migration: indexes that exist solely in a
    # migration are read as drift by `alembic revision --autogenerate` and get
    # dropped. That is exactly how the previous set was silently deleted.
    __table_args__ = (
        Index("ix_contest_session_user_id_status", "user_id", "status"),
        Index(
            "ix_contest_session_user_id_status_starts_at",
            "user_id",
            "status",
            starts_at.desc().nullslast()
        ),
    )

    def problem_slots(self) -> list[ProblemSlot]:
        """
        Return the four problem slots in problem_number order.

        A null status means the session never reached RUNNING, which matches the
        old behaviour of having no problem status row at all, so it reads as
        UNSOLVED.
        """
        return [
            ProblemSlot(
                problem_number=problem_number,
                problem_contestId=getattr(self, f"p{problem_number}_cf_contestId"),
                problem_index=getattr(self, f"p{problem_number}_cf_index"),
                problem_rating=getattr(self, f"p{problem_number}_rating"),
                status=getattr(self, f"p{problem_number}_status") or ProblemStatus.UNSOLVED.value,
                accepted_at=getattr(self, f"p{problem_number}_accepted_at"),
                solved_in_min=getattr(self, f"p{problem_number}_solved_in_min"),
            )
            for problem_number in (1, 2, 3, 4)
        ]


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

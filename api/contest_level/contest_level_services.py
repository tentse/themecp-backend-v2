from sqlalchemy.orm import Session
from .contest_level_response_models import (
    ContestLevelInput,
    ContestLevelOutput
)
from .contest_level_repository import ContestLevelRepository

class ContestLevelService:


    @staticmethod
    def get_problem_level_ratings(db: Session, level: int) -> ContestLevelOutput:
        problem_level_detail = ContestLevelRepository.get_contest_level_detail_by_level(db=db, level=level)

        return ContestLevelOutput(
            id=problem_level_detail.id,
            level=problem_level_detail.level,
            duration_in_min=problem_level_detail.duration_in_min,
            performance=problem_level_detail.performance,
            p1_rating=problem_level_detail.p1_rating,
            p2_rating=problem_level_detail.p2_rating,
            p3_rating=problem_level_detail.p3_rating,
            p4_rating=problem_level_detail.p4_rating
        )

    @staticmethod
    def get_all_contest_levels(db: Session) -> list[ContestLevelOutput]:
        contest_levels = ContestLevelRepository.get_all_contest_levels(db=db)
        return [
            ContestLevelOutput(
                id=cl.id,
                level=cl.level,
                duration_in_min=cl.duration_in_min,
                performance=cl.performance,
                p1_rating=cl.p1_rating,
                p2_rating=cl.p2_rating,
                p3_rating=cl.p3_rating,
                p4_rating=cl.p4_rating
            )
            for cl in contest_levels
        ]

    @staticmethod
    def create_contest_level(db: Session, create_contest_level: ContestLevelInput) -> ContestLevelOutput:
        contest_level = ContestLevelRepository.create_new_contest_level(
            db=db,
            create_contest_level=create_contest_level
        )
        db.commit()
        db.refresh(contest_level)

        return ContestLevelOutput(
            id=contest_level.id,
            level=contest_level.level,
            duration_in_min=contest_level.duration_in_min,
            performance=contest_level.performance,
            p1_rating=contest_level.p1_rating,
            p2_rating=contest_level.p2_rating,
            p3_rating=contest_level.p3_rating,
            p4_rating=contest_level.p4_rating
        )

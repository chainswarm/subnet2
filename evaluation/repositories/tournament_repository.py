from datetime import datetime
from typing import List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy.orm import Session

from evaluation.models.database import Tournament, Submission, EvaluationRun, TournamentResult


class TournamentRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_tournament(self, tournament: Tournament) -> Tournament:
        self.session.add(tournament)
        self.session.commit()
        self.session.refresh(tournament)
        logger.info("tournament_created", tournament_id=str(tournament.id), name=tournament.name)
        return tournament

    def get_by_id(self, tournament_id: UUID) -> Tournament:
        tournament = self.session.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not tournament:
            raise ValueError(f"tournament_not_found: {tournament_id}")
        return tournament

    def get_active_by_netuid(self, netuid: int) -> Optional[Tournament]:
        return self.session.query(Tournament).filter(
            Tournament.netuid == netuid,
            Tournament.status.in_(["registration", "active"])
        ).first()

    def update_status(self, tournament_id: UUID, status: str) -> Tournament:
        tournament = self.get_by_id(tournament_id)
        tournament.status = status
        if status == "completed":
            tournament.completed_at = datetime.utcnow()
        self.session.commit()
        logger.info("tournament_status_updated", tournament_id=str(tournament_id), status=status)
        return tournament

    def create_submission(self, submission: Submission) -> Submission:
        self.session.add(submission)
        self.session.commit()
        self.session.refresh(submission)
        logger.info("submission_created", submission_id=str(submission.id), hotkey=submission.hotkey)
        return submission

    def get_submissions_by_tournament(self, tournament_id: UUID) -> List[Submission]:
        return self.session.query(Submission).filter(
            Submission.tournament_id == tournament_id
        ).all()

    def get_validated_submissions(self, tournament_id: UUID) -> List[Submission]:
        return self.session.query(Submission).filter(
            Submission.tournament_id == tournament_id,
            Submission.status == "validated"
        ).all()

    def get_submission_by_hotkey(self, tournament_id: UUID, hotkey: str) -> Optional[Submission]:
        return self.session.query(Submission).filter(
            Submission.tournament_id == tournament_id,
            Submission.hotkey == hotkey
        ).first()

    def get_submission_by_id(self, submission_id: UUID) -> Optional[Submission]:
        return self.session.query(Submission).filter(
            Submission.id == submission_id
        ).first()

    def update_submission_status(
        self,
        submission_id: UUID,
        status: str,
        docker_image_tag: Optional[str] = None,
        error: Optional[str] = None
    ) -> Submission:
        submission = self.session.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            raise ValueError(f"submission_not_found: {submission_id}")
        submission.status = status
        if docker_image_tag:
            submission.docker_image_tag = docker_image_tag
        if error:
            submission.validation_error = error
        if status == "validated":
            submission.validated_at = datetime.utcnow()
        self.session.commit()
        logger.info("submission_status_updated", submission_id=str(submission_id), status=status)
        return submission

    def create_evaluation_run(self, run: EvaluationRun) -> EvaluationRun:
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def update_evaluation_run(
        self,
        run_id: UUID,
        status: str,
        execution_time_seconds: Optional[float] = None,
        exit_code: Optional[int] = None,
        pattern_recall: Optional[float] = None,
        data_correctness: Optional[bool] = None,
        error_message: Optional[str] = None,
    ) -> EvaluationRun:
        run = self.session.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
        if not run:
            raise ValueError(f"evaluation_run_not_found: {run_id}")
        run.status = status
        if execution_time_seconds is not None:
            run.execution_time_seconds = execution_time_seconds
        if exit_code is not None:
            run.exit_code = exit_code
        if pattern_recall is not None:
            run.pattern_recall = pattern_recall
        if data_correctness is not None:
            run.data_correctness = data_correctness
        if error_message is not None:
            run.error_message = error_message
        if status in ["completed", "failed", "timeout"]:
            run.completed_at = datetime.utcnow()
        self.session.commit()
        return run

    def get_runs_by_submission(self, submission_id: UUID) -> List[EvaluationRun]:
        return self.session.query(EvaluationRun).filter(
            EvaluationRun.submission_id == submission_id
        ).all()

    def get_runs_by_tournament(self, tournament_id: UUID) -> List[EvaluationRun]:
        return self.session.query(EvaluationRun).join(Submission).filter(
            Submission.tournament_id == tournament_id
        ).all()

    def create_result(self, result: TournamentResult) -> TournamentResult:
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)
        logger.info("result_created", tournament_id=str(result.tournament_id), hotkey=result.hotkey, rank=result.rank)
        return result

    def get_results_by_tournament(self, tournament_id: UUID) -> List[TournamentResult]:
        return self.session.query(TournamentResult).filter(
            TournamentResult.tournament_id == tournament_id
        ).order_by(TournamentResult.rank).all()

    def delete_results_by_tournament(self, tournament_id: UUID) -> int:
        count = self.session.query(TournamentResult).filter(
            TournamentResult.tournament_id == tournament_id
        ).delete()
        self.session.commit()
        return count

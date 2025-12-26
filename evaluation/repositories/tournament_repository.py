from datetime import datetime
from typing import List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy.orm import Session

from evaluation.models.database import (
    AnalyticsTournament,
    AnalyticsTournamentSubmission,
    AnalyticsTournamentEvaluationRun,
    AnalyticsTournamentResult,
)


class TournamentRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_tournament(self, tournament: AnalyticsTournament) -> AnalyticsTournament:
        self.session.add(tournament)
        self.session.commit()
        self.session.refresh(tournament)
        logger.info("tournament_created", tournament_id=str(tournament.id), epoch_number=tournament.epoch_number)
        return tournament

    def get_by_id(self, tournament_id: UUID) -> AnalyticsTournament:
        tournament = self.session.query(AnalyticsTournament).filter(AnalyticsTournament.id == tournament_id).first()
        if not tournament:
            raise ValueError(f"tournament_not_found: {tournament_id}")
        return tournament

    def get_by_epoch(self, epoch_number: int) -> Optional[AnalyticsTournament]:
        return self.session.query(AnalyticsTournament).filter(
            AnalyticsTournament.epoch_number == epoch_number
        ).first()

    def get_latest_tournament(self) -> Optional[AnalyticsTournament]:
        """Get most recent tournament by epoch number"""
        return self.session.query(AnalyticsTournament)\
            .order_by(AnalyticsTournament.epoch_number.desc())\
            .first()

    def get_active_tournament(self) -> Optional[AnalyticsTournament]:
        return self.session.query(AnalyticsTournament).filter(
            AnalyticsTournament.status.in_(["pending", "collecting", "testing", "evaluating"])
        ).first()

    def update_status(
        self,
        tournament_id: UUID,
        status: str,
        total_evaluation_runs: Optional[int] = None
    ) -> AnalyticsTournament:
        tournament = self.get_by_id(tournament_id)
        tournament.status = status
        if status == "completed":
            tournament.completed_at = datetime.utcnow()
        if total_evaluation_runs is not None:
            tournament.total_evaluation_runs = total_evaluation_runs
        self.session.commit()
        logger.info("tournament_status_updated", tournament_id=str(tournament_id), status=status)
        return tournament

    def create_submission(self, submission: AnalyticsTournamentSubmission) -> AnalyticsTournamentSubmission:
        self.session.add(submission)
        self.session.commit()
        self.session.refresh(submission)
        logger.info("submission_created", submission_id=str(submission.id), hotkey=submission.hotkey)
        return submission

    def get_submissions_by_tournament(self, tournament_id: UUID) -> List[AnalyticsTournamentSubmission]:
        return self.session.query(AnalyticsTournamentSubmission).filter(
            AnalyticsTournamentSubmission.tournament_id == tournament_id
        ).all()

    def get_validated_submissions(self, tournament_id: UUID) -> List[AnalyticsTournamentSubmission]:
        return self.session.query(AnalyticsTournamentSubmission).filter(
            AnalyticsTournamentSubmission.tournament_id == tournament_id,
            AnalyticsTournamentSubmission.status == "valid"
        ).all()

    def get_submission_by_hotkey(self, tournament_id: UUID, hotkey: str) -> Optional[AnalyticsTournamentSubmission]:
        return self.session.query(AnalyticsTournamentSubmission).filter(
            AnalyticsTournamentSubmission.tournament_id == tournament_id,
            AnalyticsTournamentSubmission.hotkey == hotkey
        ).first()

    def get_submission_by_id(self, submission_id: UUID) -> Optional[AnalyticsTournamentSubmission]:
        return self.session.query(AnalyticsTournamentSubmission).filter(
            AnalyticsTournamentSubmission.id == submission_id
        ).first()

    def update_submission_status(
        self,
        submission_id: UUID,
        status: str,
        docker_image_digest: Optional[str] = None,
        validation_error: Optional[str] = None
    ) -> AnalyticsTournamentSubmission:
        submission = self.session.query(AnalyticsTournamentSubmission).filter(
            AnalyticsTournamentSubmission.id == submission_id
        ).first()
        if not submission:
            raise ValueError(f"submission_not_found: {submission_id}")
        submission.status = status
        if docker_image_digest:
            submission.docker_image_digest = docker_image_digest
        if validation_error:
            submission.validation_error = validation_error
        if status == "valid":
            submission.validated_at = datetime.utcnow()
        self.session.commit()
        logger.info("submission_status_updated", submission_id=str(submission_id), status=status)
        return submission

    def create_evaluation_run(self, run: AnalyticsTournamentEvaluationRun) -> AnalyticsTournamentEvaluationRun:
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def update_evaluation_run(
        self,
        run_id: UUID,
        status: str,
        output_schema_valid: Optional[bool] = None,
        feature_generation_time_seconds: Optional[float] = None,
        pattern_existence: Optional[bool] = None,
        patterns_reported: Optional[int] = None,
        synthetic_addresses_expected: Optional[int] = None,
        synthetic_addresses_found: Optional[int] = None,
        novelty_patterns_valid: Optional[int] = None,
        novelty_patterns_invalid: Optional[int] = None,
        pattern_detection_time_seconds: Optional[float] = None,
        feature_performance_score: Optional[float] = None,
        synthetic_recall_score: Optional[float] = None,
        pattern_precision_score: Optional[float] = None,
        novelty_discovery_score: Optional[float] = None,
        pattern_performance_score: Optional[float] = None,
        final_score: Optional[float] = None,
        exit_code: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> AnalyticsTournamentEvaluationRun:
        run = self.session.query(AnalyticsTournamentEvaluationRun).filter(
            AnalyticsTournamentEvaluationRun.id == run_id
        ).first()
        if not run:
            raise ValueError(f"evaluation_run_not_found: {run_id}")
        run.status = status
        if output_schema_valid is not None:
            run.output_schema_valid = output_schema_valid
        if feature_generation_time_seconds is not None:
            run.feature_generation_time_seconds = feature_generation_time_seconds
        if pattern_existence is not None:
            run.pattern_existence = pattern_existence
        if patterns_reported is not None:
            run.patterns_reported = patterns_reported
        if synthetic_addresses_expected is not None:
            run.synthetic_addresses_expected = synthetic_addresses_expected
        if synthetic_addresses_found is not None:
            run.synthetic_addresses_found = synthetic_addresses_found
        if novelty_patterns_valid is not None:
            run.novelty_patterns_valid = novelty_patterns_valid
        if novelty_patterns_invalid is not None:
            run.novelty_patterns_invalid = novelty_patterns_invalid
        if pattern_detection_time_seconds is not None:
            run.pattern_detection_time_seconds = pattern_detection_time_seconds
        if feature_performance_score is not None:
            run.feature_performance_score = feature_performance_score
        if synthetic_recall_score is not None:
            run.synthetic_recall_score = synthetic_recall_score
        if pattern_precision_score is not None:
            run.pattern_precision_score = pattern_precision_score
        if novelty_discovery_score is not None:
            run.novelty_discovery_score = novelty_discovery_score
        if pattern_performance_score is not None:
            run.pattern_performance_score = pattern_performance_score
        if final_score is not None:
            run.final_score = final_score
        if exit_code is not None:
            run.exit_code = exit_code
        if error_message is not None:
            run.error_message = error_message
        if status in ["completed", "failed", "timeout"]:
            run.completed_at = datetime.utcnow()
        self.session.commit()
        return run

    def get_runs_by_submission(self, submission_id: UUID) -> List[AnalyticsTournamentEvaluationRun]:
        return self.session.query(AnalyticsTournamentEvaluationRun).filter(
            AnalyticsTournamentEvaluationRun.submission_id == submission_id
        ).all()

    def get_runs_by_tournament(self, tournament_id: UUID) -> List[AnalyticsTournamentEvaluationRun]:
        return self.session.query(AnalyticsTournamentEvaluationRun).join(
            AnalyticsTournamentSubmission
        ).filter(
            AnalyticsTournamentSubmission.tournament_id == tournament_id
        ).all()

    def create_result(self, result: AnalyticsTournamentResult) -> AnalyticsTournamentResult:
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)
        logger.info("result_created", tournament_id=str(result.tournament_id), hotkey=result.hotkey, rank=result.rank)
        return result

    def get_results_by_tournament(self, tournament_id: UUID) -> List[AnalyticsTournamentResult]:
        return self.session.query(AnalyticsTournamentResult).filter(
            AnalyticsTournamentResult.tournament_id == tournament_id
        ).order_by(AnalyticsTournamentResult.rank).all()

    def delete_results_by_tournament(self, tournament_id: UUID) -> int:
        count = self.session.query(AnalyticsTournamentResult).filter(
            AnalyticsTournamentResult.tournament_id == tournament_id
        ).delete()
        self.session.commit()
        return count

    def get_submission_by_tournament_and_uid(self, tournament_id: UUID, uid: int) -> Optional[AnalyticsTournamentSubmission]:
        """Get submission for specific tournament and miner UID."""
        return self.session.query(AnalyticsTournamentSubmission).filter(
            AnalyticsTournamentSubmission.tournament_id == tournament_id,
            AnalyticsTournamentSubmission.uid == uid,
        ).first()

    def get_completed_tournament_awaiting_weights(self) -> Optional[AnalyticsTournament]:
        """Get the oldest completed tournament without weights set."""
        return self.session.query(AnalyticsTournament).filter(
            AnalyticsTournament.status == "completed",
            AnalyticsTournament.weights_set_at.is_(None),
        ).order_by(AnalyticsTournament.started_at).first()

    def mark_weights_set(self, tournament_id: UUID):
        """Mark tournament as having weights set."""
        tournament = self.get_by_id(tournament_id)
        tournament.weights_set_at = datetime.utcnow()
        self.session.commit()
        logger.info("tournament_weights_set", tournament_id=str(tournament_id))

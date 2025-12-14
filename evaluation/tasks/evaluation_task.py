import uuid
from datetime import datetime, date
from uuid import UUID

import pandas as pd
from loguru import logger

from evaluation.db import get_session
from evaluation.managers.docker_manager import DockerManager
from evaluation.managers.scoring_manager import ScoringManager
from evaluation.managers.submission_manager import SubmissionManager
from evaluation.models.database import EvaluationRun
from evaluation.repositories.tournament_repository import TournamentRepository
from evaluation.tasks.celery_app import celery_app


def load_evaluation_dataset(tournament_id: UUID) -> pd.DataFrame:
    dataset_path = f"/data/datasets/{tournament_id}/transfers.parquet"
    return pd.read_parquet(dataset_path)


def load_ground_truth(tournament_id: UUID) -> pd.DataFrame:
    ground_truth_path = f"/data/datasets/{tournament_id}/ground_truth.parquet"
    return pd.read_parquet(ground_truth_path)


@celery_app.task(name="evaluation.run_submission")
def run_submission_task(submission_id: str, epoch_number: int = 0, network: str = "ethereum") -> dict:
    session = get_session()
    repo = TournamentRepository(session)
    submission_manager = SubmissionManager()
    docker_manager = DockerManager()
    scoring_manager = ScoringManager()

    try:
        submission = repo.get_submission_by_id(UUID(submission_id))
        if not submission:
            raise ValueError(f"submission_not_found: {submission_id}")

        if submission.status != "pending":
            raise ValueError(f"submission_not_pending: {submission.status}")

        result = submission_manager.process_submission(
            repository_url=submission.repository_url,
            commit_hash=submission.commit_hash,
            submission_id=submission.id,
        )

        if not result.success:
            repo.update_submission_status(
                submission.id,
                status="failed",
                error=result.error_message,
            )
            return {"success": False, "error": result.error_message}

        repo.update_submission_status(
            submission.id,
            status="validated",
            docker_image_tag=result.docker_image_tag,
        )

        run = EvaluationRun(
            id=uuid.uuid4(),
            submission_id=submission.id,
            epoch_number=epoch_number,
            network=network,
            test_date=date.today(),
            status="running",
            started_at=datetime.utcnow(),
        )
        run = repo.create_evaluation_run(run)

        transfers_df = load_evaluation_dataset(submission.tournament_id)

        container_result = docker_manager.run_container(
            image_tag=result.docker_image_tag,
            run_id=run.id,
            transfers_df=transfers_df,
        )

        if container_result.timed_out:
            repo.update_evaluation_run(
                run.id,
                status="timeout",
                execution_time_seconds=container_result.execution_time_seconds,
            )
            return {"success": False, "error": "timeout"}

        if container_result.exit_code != 0:
            repo.update_evaluation_run(
                run.id,
                status="failed",
                execution_time_seconds=container_result.execution_time_seconds,
                exit_code=container_result.exit_code,
                error_message=container_result.logs[:1000],
            )
            return {"success": False, "error": f"exit_code_{container_result.exit_code}"}

        output_df = docker_manager.read_output(run.id)
        if output_df is None:
            repo.update_evaluation_run(
                run.id,
                status="failed",
                execution_time_seconds=container_result.execution_time_seconds,
                error_message="no_output_file",
            )
            return {"success": False, "error": "no_output_file"}

        ground_truth_df = load_ground_truth(submission.tournament_id)

        score = scoring_manager.calculate_score(
            output_df=output_df,
            ground_truth_df=ground_truth_df,
            execution_time=container_result.execution_time_seconds,
        )

        repo.update_evaluation_run(
            run.id,
            status="completed",
            execution_time_seconds=container_result.execution_time_seconds,
            exit_code=container_result.exit_code,
            pattern_recall=score.pattern_recall,
            data_correctness=score.data_correctness,
        )

        docker_manager.cleanup_run(run.id)
        submission_manager.cleanup(submission.id)

        logger.info(
            "submission_evaluated",
            submission_id=str(submission.id),
            score=score.final_score,
        )

        return {
            "success": True,
            "score": score.final_score,
            "recall": score.pattern_recall,
        }

    finally:
        session.close()


@celery_app.task(name="evaluation.run_all_submissions")
def run_all_submissions_task(tournament_id: str) -> dict:
    session = get_session()
    repo = TournamentRepository(session)

    try:
        submissions = repo.get_submissions_by_tournament(UUID(tournament_id))
        pending = [s for s in submissions if s.status == "pending"]

        logger.info("running_all_submissions", tournament_id=tournament_id, count=len(pending))

        for submission in pending:
            run_submission_task.delay(str(submission.id))

        return {"submitted": len(pending)}

    finally:
        session.close()

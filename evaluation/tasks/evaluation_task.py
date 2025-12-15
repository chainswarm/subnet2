import uuid
from datetime import datetime, date, timedelta
from pathlib import Path
from uuid import UUID

import pandas as pd
from loguru import logger

from evaluation.db import get_session
from evaluation.managers.docker_manager import DockerManager
from evaluation.managers.scoring_manager import AnalyticsScoringManager
from evaluation.managers.submission_manager import SubmissionManager
from evaluation.models.database import AnalyticsTournamentEvaluationRun
from evaluation.repositories.tournament_repository import TournamentRepository
from evaluation.tasks.celery_app import celery_app
from config import config


def load_evaluation_dataset(tournament_id: UUID, network: str, test_date: date) -> pd.DataFrame:
    """
    Load evaluation dataset for specific network and test date.
    
    Path: {data_path}/synthetics/snapshots/{network}/{test_date}/30/transfers.parquet
    """
    dataset_path = f"{config.data_path}/synthetics/snapshots/{network}/{test_date.strftime('%Y-%m-%d')}/30/transfers.parquet"
    if not Path(dataset_path).exists():
        raise ValueError(f"dataset_not_found: {dataset_path}")
    return pd.read_parquet(dataset_path)


def load_ground_truth(tournament_id: UUID, network: str, test_date: date) -> pd.DataFrame:
    """
    Load ground truth for specific network and test date.
    
    Path: {data_path}/synthetics/snapshots/{network}/{test_date}/30/ground_truth.parquet
    """
    gt_path = f"{config.data_path}/synthetics/snapshots/{network}/{test_date.strftime('%Y-%m-%d')}/30/ground_truth.parquet"
    if not Path(gt_path).exists():
        raise ValueError(f"ground_truth_not_found: {gt_path}")
    return pd.read_parquet(gt_path)


@celery_app.task(name="evaluation.run_submission")
def run_submission_task(
    submission_id: str,
    epoch_number: int,
    network: str,
    test_date: str
) -> dict:
    """
    Run evaluation for a single submission on a specific day/network.
    
    Args:
        submission_id: UUID of the submission
        epoch_number: Day number (0-4)
        network: Network name (e.g. "torus", "bittensor", "ethereum")
        test_date: Test date in YYYY-MM-DD format
        
    Returns:
        Dict with success status and score
    """
    session = get_session()
    repo = TournamentRepository(session)
    submission_manager = SubmissionManager()
    docker_manager = DockerManager()
    scoring_manager = AnalyticsScoringManager()

    try:
        submission = repo.get_submission_by_id(UUID(submission_id))
        if not submission:
            raise ValueError(f"submission_not_found: {submission_id}")

        # Parse test_date
        test_date_obj = datetime.strptime(test_date, "%Y-%m-%d").date()

        # Build and validate submission if needed
        if submission.status == "pending":
            result = submission_manager.process_submission(
                repository_url=submission.repository_url,
                commit_hash="main",  # Use repository_url as-is
                submission_id=submission.id,
            )

            if not result.success:
                repo.update_submission_status(
                    submission.id,
                    status="invalid",
                    validation_error=result.error_message,
                )
                return {"success": False, "error": result.error_message}

            repo.update_submission_status(
                submission.id,
                status="valid",
                docker_image_digest=result.docker_image_tag,
            )

        # Get docker image
        docker_image = submission.docker_image_digest
        if not docker_image:
            raise ValueError(f"no_docker_image: {submission_id}")

        # Create evaluation run
        run = AnalyticsTournamentEvaluationRun(
            id=uuid.uuid4(),
            submission_id=submission.id,
            epoch_number=epoch_number,
            network=network,
            test_date=test_date_obj,
            status="running",
            started_at=datetime.utcnow(),
        )
        run = repo.create_evaluation_run(run)

        # Load test data
        transfers_df = load_evaluation_dataset(submission.tournament_id, network, test_date_obj)

        # Run container
        container_result = docker_manager.run_container(
            image_tag=docker_image,
            run_id=run.id,
            transfers_df=transfers_df,
        )

        if container_result.timed_out:
            repo.update_evaluation_run(
                run.id,
                status="timeout",
                exit_code=-1,
                error_message="execution_timeout",
            )
            return {"success": False, "error": "timeout"}

        if container_result.exit_code != 0:
            repo.update_evaluation_run(
                run.id,
                status="failed",
                exit_code=container_result.exit_code,
                error_message=container_result.logs[:1000],
            )
            return {"success": False, "error": f"exit_code_{container_result.exit_code}"}

        # Read both output files
        features_df = docker_manager.read_features(run.id)
        patterns_df = docker_manager.read_patterns(run.id)

        if features_df is None or patterns_df is None:
            repo.update_evaluation_run(
                run.id,
                status="failed",
                exit_code=container_result.exit_code,
                error_message="missing_output_files",
            )
            return {"success": False, "error": "missing_output"}

        # Load ground truth
        ground_truth_df = load_ground_truth(submission.tournament_id, network, test_date_obj)

        # Estimate timing (20% features, 80% patterns)
        total_time = container_result.execution_time_seconds
        feature_time = total_time * 0.2
        pattern_time = total_time * 0.8

        # Calculate comprehensive score
        score = scoring_manager.calculate_score(
            features_df=features_df,
            patterns_df=patterns_df,
            transfers_df=transfers_df,
            ground_truth_df=ground_truth_df,
            feature_generation_time=feature_time,
            pattern_detection_time=pattern_time,
        )

        # Store ALL score components
        repo.update_evaluation_run(
            run.id,
            status="completed",
            output_schema_valid=score.output_schema_valid,
            feature_generation_time_seconds=score.feature_generation_time,
            pattern_existence=score.pattern_existence,
            patterns_reported=score.patterns_reported,
            synthetic_addresses_expected=score.synthetic_addresses_expected,
            synthetic_addresses_found=score.synthetic_addresses_found,
            novelty_patterns_valid=score.novelty_valid,
            novelty_patterns_invalid=score.novelty_invalid,
            pattern_detection_time_seconds=score.pattern_detection_time,
            feature_performance_score=score.feature_performance_score,
            synthetic_recall_score=score.synthetic_recall_score,
            pattern_precision_score=score.pattern_precision_score,
            novelty_discovery_score=score.novelty_discovery_score,
            pattern_performance_score=score.pattern_performance_score,
            final_score=score.final_score,
            exit_code=container_result.exit_code,
        )

        # Cleanup
        docker_manager.cleanup_run(run.id)

        logger.info(
            "evaluation_completed",
            submission_id=str(submission.id),
            network=network,
            epoch=epoch_number,
            final_score=score.final_score,
        )

        return {
            "success": True,
            "score": score.final_score,
            "network": network,
            "epoch": epoch_number,
        }

    except Exception as e:
        logger.error("evaluation_error", submission_id=submission_id, error=str(e))
        return {"success": False, "error": str(e)}

    finally:
        session.close()


@celery_app.task(name="evaluation.run_all_submissions")
def run_all_submissions_task(tournament_id: str) -> dict:
    """
    Queue evaluation runs for all submissions across multiple days and networks.
    
    Creates: evaluation_days × len(test_networks) runs per submission.
    Default: 5 days × 3 networks = 15 runs per submission.
    
    Args:
        tournament_id: UUID of the tournament
        
    Returns:
        Dict with total runs queued
    """
    session = get_session()
    repo = TournamentRepository(session)

    try:
        tournament = repo.get_by_id(UUID(tournament_id))
        submissions = repo.get_validated_submissions(UUID(tournament_id))

        evaluation_days = tournament.config.get("evaluation_days", 5)
        test_networks = tournament.test_networks
        base_date = tournament.started_at.date()

        queued = 0

        # Multi-day × multi-network loop
        for submission in submissions:
            for day in range(evaluation_days):
                for network in test_networks:
                    test_date = base_date + timedelta(days=day)
                    
                    # Queue evaluation task
                    run_submission_task.delay(
                        submission_id=str(submission.id),
                        epoch_number=day,
                        network=network,
                        test_date=test_date.strftime("%Y-%m-%d"),
                    )
                    queued += 1

        # Update tournament with total expected runs
        repo.update_status(
            tournament.id,
            "evaluating",
            total_evaluation_runs=queued
        )

        logger.info(
            "evaluation_runs_queued",
            tournament_id=tournament_id,
            submissions=len(submissions),
            evaluation_days=evaluation_days,
            test_networks=test_networks,
            total_runs=queued,
        )

        return {
            "total_runs_queued": queued,
            "submissions": len(submissions),
            "runs_per_submission": evaluation_days * len(test_networks),
        }

    finally:
        session.close()

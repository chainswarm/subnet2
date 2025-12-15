import uuid
from datetime import datetime
from typing import List

import bittensor as bt
from loguru import logger

from evaluation.db import get_session
from evaluation.models.database import AnalyticsTournament, AnalyticsTournamentSubmission
from evaluation.repositories.tournament_repository import TournamentRepository
from evaluation.tasks.celery_app import celery_app
from template.protocol import SubmissionSynapse
from config import config


def collect_submissions_from_miners(
    dendrite: bt.Dendrite,
    metagraph: bt.Metagraph,
    tournament: AnalyticsTournament,
) -> List[dict]:
    synapse = SubmissionSynapse(
        tournament_id=str(tournament.id),
        epoch_number=0,
    )

    axons = [metagraph.axons[uid] for uid in range(metagraph.n.item())]

    responses = dendrite.query(
        axons=axons,
        synapse=synapse,
        timeout=config.submission_timeout_seconds,
    )

    submissions = []
    for uid, response in enumerate(responses):
        if response.repository_url and response.commit_hash:
            submissions.append({
                "uid": uid,
                "hotkey": metagraph.hotkeys[uid],
                "repository_url": response.repository_url,
                "commit_hash": response.commit_hash,
            })

    logger.info("submissions_collected", count=len(submissions), total_miners=len(axons))
    return submissions


@celery_app.task(name="evaluation.epoch_start")
def epoch_start_task(epoch_number: int = None) -> str:
    """
    Start a new analytics tournament epoch.
    
    Creates tournament record, collects submissions from miners via SubmissionSynapse,
    and schedules the orchestrator task.
    
    Args:
        epoch_number: Optional. If None, auto-increment from last tournament.
        
    Returns:
        Tournament ID as string
    """
    session = get_session()
    repo = TournamentRepository(session)

    try:
        # Check if we should run based on schedule mode
        if config.tournament_schedule_mode == "manual":
            if epoch_number is None:
                logger.warning("manual_mode_requires_epoch_number")
                return None
        
        # Auto-increment epoch if not provided
        if epoch_number is None:
            last_tournament = repo.get_latest_tournament()
            epoch_number = (last_tournament.epoch_number + 1) if last_tournament else 1
        
        # Check if epoch already exists
        existing = repo.get_by_epoch(epoch_number)
        if existing:
            raise ValueError(f"epoch_already_exists: {epoch_number}")

        # Check for active tournament
        active = repo.get_active_tournament()
        if active:
            raise ValueError(f"active_tournament_exists: epoch {active.epoch_number}")

        now = datetime.utcnow()
        
        # Create analytics tournament with config from settings
        tournament = AnalyticsTournament(
            id=uuid.uuid4(),
            epoch_number=epoch_number,
            status="pending",
            started_at=now,
            total_submissions=0,
            total_evaluation_runs=0,
            config={
                "submission_duration_seconds": config.tournament_submission_duration_seconds,
                "epoch_count": config.tournament_epoch_count,
                "epoch_duration_seconds": config.tournament_epoch_duration_seconds,
                "baseline_repository": "https://github.com/chainswarm/analyzers-baseline",
                "baseline_version": "0.1.3",
            },
            test_networks=config.tournament_networks_list,
            created_at=now,
        )
        tournament = repo.create_tournament(tournament)

        # Initialize Bittensor components
        wallet = bt.Wallet(name=config.wallet_name, hotkey=config.wallet_hotkey)
        subtensor = bt.Subtensor(network=config.subtensor_network)
        # TODO: Get netuid from config
        netuid = 1
        metagraph = subtensor.metagraph(netuid=netuid)
        dendrite = bt.Dendrite(wallet=wallet)

        # Collect submissions from all miners
        submissions_data = collect_submissions_from_miners(dendrite, metagraph, tournament)

        # Create submission records
        for sub_data in submissions_data:
            submission = AnalyticsTournamentSubmission(
                id=uuid.uuid4(),
                tournament_id=tournament.id,
                hotkey=sub_data["hotkey"],
                uid=sub_data["uid"],
                docker_image_digest="",  # Will be filled after build
                repository_url=sub_data["repository_url"],
                status="pending",
                submitted_at=now,
            )
            repo.create_submission(submission)

        # Update tournament status and counts
        tournament.total_submissions = len(submissions_data)
        repo.update_status(tournament.id, "collecting")
        
        # Schedule orchestrator task
        from evaluation.tasks.epoch_orchestrator_task import orchestrate_tournament_task
        orchestrate_tournament_task.apply_async(
            args=[str(tournament.id)],
            countdown=5,  # Start after 5 seconds
        )

        logger.info(
            "epoch_started",
            tournament_id=str(tournament.id),
            epoch_number=epoch_number,
            submissions=len(submissions_data),
            test_networks=tournament.test_networks,
        )

        return str(tournament.id)

    finally:
        session.close()

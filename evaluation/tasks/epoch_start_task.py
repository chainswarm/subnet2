import uuid
from datetime import datetime, timedelta
from typing import List

import bittensor as bt
from loguru import logger

from evaluation.db import get_session
from evaluation.models.database import Tournament, Submission
from evaluation.repositories.tournament_repository import TournamentRepository
from evaluation.tasks.celery_app import celery_app
from template.protocol import SubmissionSynapse
from config import config


def collect_submissions_from_miners(
    dendrite: bt.Dendrite,
    metagraph: bt.Metagraph,
    tournament: Tournament,
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
def epoch_start_task(netuid: int, tournament_name: str) -> str:
    session = get_session()
    repo = TournamentRepository(session)

    try:
        existing = repo.get_active_by_netuid(netuid)
        if existing:
            raise ValueError(f"active_tournament_exists: {existing.id}")

        now = datetime.utcnow()
        tournament = Tournament(
            id=uuid.uuid4(),
            netuid=netuid,
            name=tournament_name,
            status="registration",
            registration_start=now,
            registration_end=now + timedelta(hours=1),
            start_block=0,
            end_block=360,
            epoch_blocks=360,
            test_networks=["ethereum", "bsc"],
            created_at=now,
        )
        tournament = repo.create_tournament(tournament)

        wallet = bt.Wallet(name=config.wallet_name, hotkey=config.wallet_hotkey)
        subtensor = bt.Subtensor(network=config.subtensor_network)
        metagraph = subtensor.metagraph(netuid=netuid)
        dendrite = bt.Dendrite(wallet=wallet)

        submissions_data = collect_submissions_from_miners(dendrite, metagraph, tournament)

        for sub_data in submissions_data:
            submission = Submission(
                id=uuid.uuid4(),
                tournament_id=tournament.id,
                uid=sub_data["uid"],
                hotkey=sub_data["hotkey"],
                repository_url=sub_data["repository_url"],
                commit_hash=sub_data["commit_hash"],
                status="pending",
                submitted_at=now,
            )
            repo.create_submission(submission)

        repo.update_status(tournament.id, "active")

        logger.info(
            "epoch_started",
            tournament_id=str(tournament.id),
            submissions=len(submissions_data),
        )

        return str(tournament.id)

    finally:
        session.close()

from typing import List
from uuid import UUID

import bittensor as bt
import torch
from loguru import logger

from evaluation.db import get_session
from evaluation.models.database import TournamentResult
from evaluation.models.results import ScoreResult
from evaluation.repositories.tournament_repository import TournamentRepository
from evaluation.tasks.celery_app import celery_app
from config import config


def calculate_final_rankings(
    repo: TournamentRepository,
    tournament_id: UUID,
) -> List[tuple]:
    runs = repo.get_runs_by_tournament(tournament_id)

    submission_scores = {}
    for run in runs:
        if run.status != "completed":
            continue

        submission = run.submission
        if submission.id not in submission_scores:
            submission_scores[submission.id] = {
                "hotkey": submission.hotkey,
                "uid": submission.uid,
                "scores": [],
            }

        submission_scores[submission.id]["scores"].append(
            ScoreResult(
                pattern_recall=run.pattern_recall or 0.0,
                data_correctness=run.data_correctness or False,
                execution_time=run.execution_time_seconds or 0.0,
                final_score=(run.pattern_recall or 0.0) * 0.7 + max(0, 1 - (run.execution_time_seconds or 0) / 300) * 0.3,
            )
        )

    aggregated = []

    for sub_id, data in submission_scores.items():
        if not data["scores"]:
            continue
        avg_recall = sum(s.pattern_recall for s in data["scores"]) / len(data["scores"])
        avg_correctness = all(s.data_correctness for s in data["scores"])
        avg_execution = sum(s.execution_time for s in data["scores"]) / len(data["scores"])
        avg_score = sum(s.final_score for s in data["scores"]) / len(data["scores"])
        aggregated.append((
            data["hotkey"],
            data["uid"],
            ScoreResult(
                pattern_recall=avg_recall,
                data_correctness=avg_correctness,
                execution_time=avg_execution,
                final_score=avg_score,
            ),
        ))

    sorted_results = sorted(aggregated, key=lambda x: x[2].final_score, reverse=True)

    rankings = []
    total_score = sum(x[2].final_score for x in sorted_results)
    for rank, (hotkey, uid, score) in enumerate(sorted_results, start=1):
        weight = score.final_score / total_score if total_score > 0 else 0.0
        rankings.append((hotkey, uid, rank, weight, score))

    return rankings


def set_weights_on_chain(
    netuid: int,
    rankings: List[tuple],
) -> bool:
    wallet = bt.wallet(name=config.wallet_name, hotkey=config.wallet_hotkey)
    subtensor = bt.subtensor(network=config.subtensor_network)
    metagraph = subtensor.metagraph(netuid=netuid)

    weights = torch.zeros(metagraph.n.item())
    for hotkey, uid, rank, weight, score in rankings:
        if uid < len(weights):
            weights[uid] = weight

    uids = torch.arange(metagraph.n.item())

    result = subtensor.set_weights(
        wallet=wallet,
        netuid=netuid,
        uids=uids,
        weights=weights,
        wait_for_inclusion=True,
        wait_for_finalization=False,
    )

    logger.info("weights_set", netuid=netuid, success=result)
    return result


@celery_app.task(name="evaluation.epoch_end")
def epoch_end_task(tournament_id: str) -> dict:
    session = get_session()
    repo = TournamentRepository(session)

    try:
        tournament = repo.get_by_id(UUID(tournament_id))

        if tournament.status != "active":
            raise ValueError(f"tournament_not_active: {tournament.status}")

        rankings = calculate_final_rankings(repo, tournament.id)

        repo.delete_results_by_tournament(tournament.id)

        winner_hotkey = rankings[0][0] if rankings else None

        for hotkey, uid, rank, weight, score in rankings:
            time_score = max(0.0, 1.0 - score.execution_time / 300)
            result = TournamentResult(
                tournament_id=tournament.id,
                hotkey=hotkey,
                uid=uid,
                pattern_accuracy_score=score.pattern_recall,
                data_correctness_score=1.0 if score.data_correctness else 0.0,
                performance_score=time_score,
                final_score=score.final_score,
                rank=rank,
                beat_baseline=score.final_score > 0.5,
                is_winner=(hotkey == winner_hotkey),
            )
            repo.create_result(result)

        success = set_weights_on_chain(tournament.netuid, rankings)

        repo.update_status(tournament.id, "completed")

        logger.info(
            "epoch_ended",
            tournament_id=tournament_id,
            participants=len(rankings),
            weights_set=success,
        )

        return {
            "success": True,
            "participants": len(rankings),
            "weights_set": success,
            "winner": winner_hotkey,
        }

    finally:
        session.close()

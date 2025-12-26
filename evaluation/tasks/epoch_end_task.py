from typing import List, Dict, Tuple
from uuid import UUID

from loguru import logger

from evaluation.db import get_session
from evaluation.models.database import AnalyticsTournamentResult
from evaluation.repositories.tournament_repository import TournamentRepository
from evaluation.tasks.celery_app import celery_app


def calculate_final_rankings(
    repo: TournamentRepository,
    tournament_id: UUID,
) -> List[Tuple[str, int, int, float, Dict]]:
    """
    Calculate rankings with STRICT multi-day disqualification.
    
    Rules:
    - ANY run with status="failed" OR "timeout" → ENTIRE submission disqualified
    - Must have ALL expected runs completed
    - Aggregate scores across all successful runs
    
    Returns:
        List of (hotkey, uid, rank, weight, aggregate_metrics)
    """
    tournament = repo.get_by_id(tournament_id)
    runs = repo.get_runs_by_tournament(tournament_id)
    
    # Calculate expected runs per submission
    # NEW: epoch_count × 1 network per epoch (not epoch_count × all networks)
    epoch_count = tournament.get_epoch_count()
    expected_runs_per_submission = epoch_count

    # Group runs by submission
    submission_runs = {}
    for run in runs:
        submission = run.submission
        if submission.id not in submission_runs:
            submission_runs[submission.id] = {
                "hotkey": submission.hotkey,
                "uid": submission.uid,
                "runs": [],
            }
        submission_runs[submission.id]["runs"].append(run)

    aggregated = []
    disqualified_count = 0

    # Process each submission
    for sub_id, data in submission_runs.items():
        runs_list = data["runs"]
        
        # CRITICAL: Check for ANY failures
        failed_runs = [r for r in runs_list if r.status in ["failed", "timeout"]]
        
        if failed_runs:
            # DISQUALIFY ENTIRE SUBMISSION
            repo.update_submission_status(
                sub_id,
                status="invalid",
                validation_error=f"Disqualified: {len(failed_runs)} failed/timeout runs"
            )
            
            disqualified_count += 1
            
            logger.warning(
                "submission_disqualified",
                submission_id=str(sub_id),
                hotkey=data["hotkey"],
                failed_count=len(failed_runs),
                failed_runs=[
                    {"day": r.epoch_number, "network": r.network, "status": r.status}
                    for r in failed_runs
                ],
            )
            continue

        # Verify all expected runs present
        completed_runs = [r for r in runs_list if r.status == "completed"]
        
        if len(completed_runs) != expected_runs_per_submission:
            repo.update_submission_status(
                sub_id,
                status="invalid",
                validation_error=f"Incomplete: {len(completed_runs)}/{expected_runs_per_submission} runs"
            )
            disqualified_count += 1
            logger.warning(
                "submission_incomplete",
                submission_id=str(sub_id),
                hotkey=data["hotkey"],
                completed=len(completed_runs),
                expected=expected_runs_per_submission,
            )
            continue

        # Calculate aggregate metrics across ALL runs
        avg_schema_valid_rate = sum(1 for r in completed_runs if r.output_schema_valid) / len(completed_runs)
        avg_pattern_exist_rate = sum(1 for r in completed_runs if r.pattern_existence) / len(completed_runs)
        avg_feature_perf = sum(r.feature_performance_score or 0.0 for r in completed_runs) / len(completed_runs)
        avg_synthetic = sum(r.synthetic_recall_score or 0.0 for r in completed_runs) / len(completed_runs)
        avg_precision = sum(r.pattern_precision_score or 0.0 for r in completed_runs) / len(completed_runs)
        avg_novelty = sum(r.novelty_discovery_score or 0.0 for r in completed_runs) / len(completed_runs)
        avg_pattern_perf = sum(r.pattern_performance_score or 0.0 for r in completed_runs) / len(completed_runs)
        avg_final = sum(r.final_score or 0.0 for r in completed_runs) / len(completed_runs)

        aggregated.append((
            data["hotkey"],
            data["uid"],
            {
                "output_schema_validity_rate": avg_schema_valid_rate,
                "pattern_existence_rate": avg_pattern_exist_rate,
                "feature_performance_score": avg_feature_perf,
                "synthetic_recall_score": avg_synthetic,
                "pattern_precision_score": avg_precision,
                "novelty_discovery_score": avg_novelty,
                "pattern_performance_score": avg_pattern_perf,
                "final_score": avg_final,
                "total_runs": len(completed_runs),
                "total_patterns_reported": sum(r.patterns_reported or 0 for r in completed_runs),
                "total_synthetic_found": sum(r.synthetic_addresses_found or 0 for r in completed_runs),
                "total_novelty_valid": sum(r.novelty_patterns_valid or 0 for r in completed_runs),
                "total_novelty_invalid": sum(r.novelty_patterns_invalid or 0 for r in completed_runs),
            },
        ))

    # Sort by final score
    sorted_results = sorted(aggregated, key=lambda x: x[2]["final_score"], reverse=True)

    # Calculate normalized weights
    total_score = sum(x[2]["final_score"] for x in sorted_results)
    
    rankings = []
    for rank, (hotkey, uid, metrics) in enumerate(sorted_results, start=1):
        weight = metrics["final_score"] / total_score if total_score > 0 else 0.0
        rankings.append((hotkey, uid, rank, weight, metrics))

    logger.info(
        "rankings_calculated",
        tournament_id=str(tournament_id),
        qualified=len(rankings),
        disqualified=disqualified_count,
    )

    return rankings


def epoch_end_task(tournament_id: str) -> dict:
    """
    Calculate final rankings and prepare results for validator weight-setting.
    
    Implements STRICT disqualification:
    - ANY failed/timeout run → submission excluded
    - Only fully-successful submissions ranked
    
    The validator will poll the DB and set weights when it detects completed status.
    
    Args:
        tournament_id: UUID of the tournament
        
    Returns:
        Dict with results
    """
    session = get_session()
    repo = TournamentRepository(session)

    try:
        tournament = repo.get_by_id(UUID(tournament_id))

        if tournament.status not in ["in_progress", "evaluating"]:
            raise ValueError(f"tournament_not_ready: {tournament.status}")

        # Calculate rankings with strict disqualification
        rankings = calculate_final_rankings(repo, tournament.id)

        # Clear old results (idempotency)
        repo.delete_results_by_tournament(tournament.id)

        winner_hotkey = rankings[0][0] if rankings else None

        # Create result records
        for hotkey, uid, rank, weight, metrics in rankings:
            result = AnalyticsTournamentResult(
                tournament_id=tournament.id,
                hotkey=hotkey,
                uid=uid,
                output_schema_validity_rate=metrics["output_schema_validity_rate"],
                pattern_existence_rate=metrics["pattern_existence_rate"],
                feature_performance_score=metrics["feature_performance_score"],
                synthetic_recall_score=metrics["synthetic_recall_score"],
                pattern_precision_score=metrics["pattern_precision_score"],
                novelty_discovery_score=metrics["novelty_discovery_score"],
                pattern_performance_score=metrics["pattern_performance_score"],
                total_runs=metrics["total_runs"],
                total_patterns_reported=metrics["total_patterns_reported"],
                total_synthetic_found=metrics["total_synthetic_found"],
                total_novelty_valid=metrics["total_novelty_valid"],
                total_novelty_invalid=metrics["total_novelty_invalid"],
                final_score=metrics["final_score"],
                rank=rank,
                beat_baseline=metrics["final_score"] > 0.5,
                is_winner=(hotkey == winner_hotkey),
            )
            repo.create_result(result)

        # Mark tournament complete (validator will set weights)
        repo.update_status(tournament.id, "completed")

        logger.info(
            "epoch_ended",
            tournament_id=tournament_id,
            epoch_number=tournament.epoch_number,
            participants=len(rankings),
            weights_set=False,  # Validator will poll and set
            winner=winner_hotkey,
        )

        return {
            "success": True,
            "epoch_number": tournament.epoch_number,
            "participants": len(rankings),
            "weights_set": False,  # Validator will poll and set
            "winner": winner_hotkey,
        }

    finally:
        session.close()

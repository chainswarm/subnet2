"""
Analytics Tournament statistics router endpoints.

Provides aggregate statistics and KPIs for Analytics tournaments,
including miner history and epoch-level stats.

API prefix: /api/v1/analytics/stats/
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from evaluation.api.dependencies import get_db
from evaluation.api.models.responses import (
    StatsResponse,
    MinerHistoryResponse,
    TournamentResultResponse,
    EpochStatsResponse,
)
from evaluation.models.database import (
    AnalyticsTournament,
    AnalyticsTournamentSubmission,
    AnalyticsTournamentEvaluationRun,
    AnalyticsTournamentResult,
)


router = APIRouter(prefix="/api/v1/analytics", tags=["Stats"])


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get Tournament Statistics",
    description="""
Retrieve aggregate statistics for all tournaments.

### Available Metrics

**Tournament Counts:**
- Active tournaments currently running
- Completed tournaments

**Participation:**
- Total unique miners
- Total submissions across all tournaments
- Total evaluation runs completed

**Score Averages:**
- Average synthetic recall (ground_truth detection)
- Average pattern precision (anti-cheat)
- Average novelty discovery score

**Novelty Discovery:**
- Total novel patterns discovered by all miners

**Performance:**
- Baseline beat rate (% of miners exceeding baseline)

### Caching
This endpoint aggregates data from multiple tables. Consider
caching for 30-60 seconds on high-traffic dashboards.
    """,
    response_description="Aggregate tournament statistics",
    responses={
        200: {
            "description": "Successfully retrieved statistics",
            "content": {
                "application/json": {
                    "example": {
                        "active_tournaments": 1,
                        "completed_tournaments": 12,
                        "total_miners": 127,
                        "total_submissions": 452,
                        "total_runs_completed": 2451,
                        "avg_synthetic_recall": 0.847,
                        "avg_pattern_precision": 0.912,
                        "avg_novelty_discovery": 0.287,
                        "total_novelty_patterns_found": 12847,
                        "baseline_beat_rate": 0.673
                    }
                }
            }
        }
    },
)
async def get_stats(db: Session = Depends(get_db)):
    """
    Get aggregate statistics for tournaments.
    
    Calculates real-time metrics across all tournaments.
    Returns null for ratio metrics when there is no data.
    """
    # Count tournaments by status
    active_tournaments = db.query(func.count(AnalyticsTournament.id)).filter(
        AnalyticsTournament.status.in_(["in_progress", "evaluating"])
    ).scalar() or 0
    
    completed_tournaments = db.query(func.count(AnalyticsTournament.id)).filter(
        AnalyticsTournament.status == "completed"
    ).scalar() or 0
    
    # Count unique miners
    total_miners = db.query(
        func.count(func.distinct(AnalyticsTournamentSubmission.hotkey))
    ).scalar() or 0
    
    # Count all submissions
    total_submissions = db.query(
        func.count(AnalyticsTournamentSubmission.id)
    ).scalar() or 0
    
    # Count completed runs
    total_runs_completed = db.query(
        func.count(AnalyticsTournamentEvaluationRun.id)
    ).filter(
        AnalyticsTournamentEvaluationRun.status == "completed"
    ).scalar() or 0
    
    # Calculate average scores
    avg_synthetic_recall = db.query(
        func.avg(AnalyticsTournamentEvaluationRun.synthetic_recall_score)
    ).filter(
        AnalyticsTournamentEvaluationRun.synthetic_recall_score.isnot(None)
    ).scalar()
    
    avg_pattern_precision = db.query(
        func.avg(AnalyticsTournamentEvaluationRun.pattern_precision_score)
    ).filter(
        AnalyticsTournamentEvaluationRun.pattern_precision_score.isnot(None)
    ).scalar()
    
    avg_novelty_discovery = db.query(
        func.avg(AnalyticsTournamentEvaluationRun.novelty_discovery_score)
    ).filter(
        AnalyticsTournamentEvaluationRun.novelty_discovery_score.isnot(None)
    ).scalar()
    
    # Total novelty patterns found
    total_novelty = db.query(
        func.sum(AnalyticsTournamentEvaluationRun.novelty_patterns_valid)
    ).filter(
        AnalyticsTournamentEvaluationRun.novelty_patterns_valid.isnot(None)
    ).scalar()
    
    # Baseline beat rate
    total_results = db.query(func.count(AnalyticsTournamentResult.id)).scalar() or 0
    baseline_beats = db.query(func.count(AnalyticsTournamentResult.id)).filter(
        AnalyticsTournamentResult.beat_baseline == True  # noqa: E712
    ).scalar() or 0
    
    baseline_beat_rate = None
    if total_results > 0:
        baseline_beat_rate = baseline_beats / total_results
    
    return StatsResponse(
        active_tournaments=active_tournaments,
        completed_tournaments=completed_tournaments,
        total_miners=total_miners,
        total_submissions=total_submissions,
        total_runs_completed=total_runs_completed,
        avg_synthetic_recall=float(avg_synthetic_recall) if avg_synthetic_recall else None,
        avg_pattern_precision=float(avg_pattern_precision) if avg_pattern_precision else None,
        avg_novelty_discovery=float(avg_novelty_discovery) if avg_novelty_discovery else None,
        total_novelty_patterns_found=int(total_novelty) if total_novelty else None,
        baseline_beat_rate=baseline_beat_rate,
    )


@router.get(
    "/stats/miners/{hotkey}",
    response_model=MinerHistoryResponse,
    summary="Get Miner History",
    description="""
Retrieve complete tournament history for a specific miner.

### Aggregate Statistics
- Total tournaments participated
- Tournament wins
- Baseline beat count
- Average scores across all tournaments

### Score Averages
- Average synthetic recall
- Average pattern precision
- Average novelty discovery

### Discovery Stats
- Total novel patterns discovered across all tournaments

### Recent Results
Full results from recent tournaments, sorted newest first.

The hotkey should be the miner's Bittensor SS58 address.
    """,
    response_description="Miner's complete tournament history",
    responses={
        200: {"description": "Successfully retrieved miner history"},
        404: {"description": "Miner not found (no submissions)"},
    },
)
async def get_miner_history(
    hotkey: str,
    limit: int = Query(
        default=10,
        le=50,
        description="Maximum recent results to return",
    ),
    db: Session = Depends(get_db),
):
    """
    Get complete tournament history for a miner.
    
    Calculates aggregate statistics and returns recent tournament results.
    """
    # Check if miner exists
    submission_count = db.query(func.count(AnalyticsTournamentSubmission.id)).filter(
        AnalyticsTournamentSubmission.hotkey == hotkey
    ).scalar()
    
    if not submission_count:
        raise HTTPException(status_code=404, detail="miner_not_found")
    
    # Get all results for this miner
    results = db.query(AnalyticsTournamentResult).filter(
        AnalyticsTournamentResult.hotkey == hotkey
    ).order_by(AnalyticsTournamentResult.calculated_at.desc()).all()
    
    # Calculate aggregates
    total_tournaments = len(results)
    total_wins = sum(1 for r in results if r.is_winner)
    total_baseline_beats = sum(1 for r in results if r.beat_baseline)
    
    # Average scores
    final_scores = [r.final_score for r in results if r.final_score is not None]
    avg_final = sum(final_scores) / len(final_scores) if final_scores else None
    
    ranks = [r.rank for r in results if r.rank is not None]
    avg_rank = sum(ranks) / len(ranks) if ranks else None
    best_rank = min(ranks) if ranks else None
    
    synthetic_recalls = [
        r.synthetic_recall_score for r in results 
        if r.synthetic_recall_score is not None
    ]
    avg_synthetic = sum(synthetic_recalls) / len(synthetic_recalls) if synthetic_recalls else None
    
    precisions = [
        r.pattern_precision_score for r in results 
        if r.pattern_precision_score is not None
    ]
    avg_precision = sum(precisions) / len(precisions) if precisions else None
    
    novelties = [
        r.novelty_discovery_score for r in results 
        if r.novelty_discovery_score is not None
    ]
    avg_novelty = sum(novelties) / len(novelties) if novelties else None
    
    # Total novelty patterns found
    total_novelty_found = sum(
        r.total_novelty_valid for r in results 
        if r.total_novelty_valid is not None
    )
    
    # Format recent results
    recent_results = [
        TournamentResultResponse(
            id=str(r.id),
            tournament_id=str(r.tournament_id),
            hotkey=r.hotkey,
            uid=r.uid,
            output_schema_validity_rate=r.output_schema_validity_rate,
            pattern_existence_rate=r.pattern_existence_rate,
            feature_performance_score=r.feature_performance_score,
            synthetic_recall_score=r.synthetic_recall_score,
            pattern_precision_score=r.pattern_precision_score,
            novelty_discovery_score=r.novelty_discovery_score,
            pattern_performance_score=r.pattern_performance_score,
            total_runs=r.total_runs,
            total_patterns_reported=r.total_patterns_reported,
            total_synthetic_found=r.total_synthetic_found,
            total_novelty_valid=r.total_novelty_valid,
            total_novelty_invalid=r.total_novelty_invalid,
            final_score=r.final_score,
            rank=r.rank,
            beat_baseline=r.beat_baseline,
            is_winner=r.is_winner,
            calculated_at=r.calculated_at,
        )
        for r in results[:limit]
    ]
    
    return MinerHistoryResponse(
        hotkey=hotkey,
        total_tournaments=total_tournaments,
        total_wins=total_wins,
        total_baseline_beats=total_baseline_beats,
        average_final_score=avg_final,
        average_rank=avg_rank,
        best_rank=best_rank,
        avg_synthetic_recall=avg_synthetic,
        avg_pattern_precision=avg_precision,
        avg_novelty_discovery=avg_novelty,
        total_novelty_patterns_found=total_novelty_found if total_novelty_found > 0 else None,
        recent_results=recent_results,
    )


@router.get(
    "/stats/epochs/{epoch_number}",
    response_model=EpochStatsResponse,
    summary="Get Epoch Statistics",
    description="""
Retrieve statistics for a specific epoch's tournament.

Returns detailed metrics for the specified epoch, useful for
tracking performance trends over time.

### Metrics
- Participant count
- Total runs
- Average and top scores
- Component score averages (recall, precision, novelty)
- Winner info (if completed)
- Novelty discoveries
- Baseline beat count
    """,
    response_description="Epoch-level statistics",
    responses={
        200: {"description": "Successfully retrieved epoch statistics"},
        404: {"description": "No data found for this epoch"},
    },
)
async def get_epoch_stats(
    epoch_number: int,
    db: Session = Depends(get_db),
):
    """Get statistics for a specific epoch."""
    # Check if epoch exists
    tournament = db.query(AnalyticsTournament).filter(
        AnalyticsTournament.epoch_number == epoch_number
    ).first()
    
    if not tournament:
        raise HTTPException(status_code=404, detail="epoch_not_found")
    
    # Get runs for this epoch
    runs = db.query(AnalyticsTournamentEvaluationRun).filter(
        AnalyticsTournamentEvaluationRun.epoch_number == epoch_number
    ).all()
    
    completed_runs = [r for r in runs if r.status == "completed"]
    
    # Calculate averages
    final_scores = [
        r.final_score for r in completed_runs 
        if r.final_score is not None
    ]
    avg_final = sum(final_scores) / len(final_scores) if final_scores else None
    top_score = max(final_scores) if final_scores else None
    
    synthetic_recalls = [
        r.synthetic_recall_score for r in completed_runs 
        if r.synthetic_recall_score is not None
    ]
    avg_synthetic = sum(synthetic_recalls) / len(synthetic_recalls) if synthetic_recalls else None
    
    precisions = [
        r.pattern_precision_score for r in completed_runs 
        if r.pattern_precision_score is not None
    ]
    avg_precision = sum(precisions) / len(precisions) if precisions else None
    
    novelties = [
        r.novelty_discovery_score for r in completed_runs 
        if r.novelty_discovery_score is not None
    ]
    avg_novelty = sum(novelties) / len(novelties) if novelties else None
    
    # Total novelty patterns
    total_novelty = sum(
        r.novelty_patterns_valid for r in completed_runs 
        if r.novelty_patterns_valid is not None
    )
    
    # Get results for baseline beat count and winner
    results = db.query(AnalyticsTournamentResult).filter(
        AnalyticsTournamentResult.tournament_id == tournament.id
    ).all()
    
    baseline_beat_count = sum(1 for r in results if r.beat_baseline)
    
    # Find winner
    winner = next((r for r in results if r.is_winner), None)
    winner_hotkey = winner.hotkey if winner else None
    winner_score = winner.final_score if winner else None
    
    # Count unique miners
    total_participants = db.query(
        func.count(func.distinct(AnalyticsTournamentSubmission.hotkey))
    ).filter(
        AnalyticsTournamentSubmission.tournament_id == tournament.id
    ).scalar() or 0
    
    return EpochStatsResponse(
        epoch_number=epoch_number,
        tournament_id=str(tournament.id),
        status=tournament.status,
        total_participants=total_participants,
        total_runs=len(completed_runs),
        avg_final_score=avg_final,
        top_score=top_score,
        avg_synthetic_recall=avg_synthetic,
        avg_pattern_precision=avg_precision,
        avg_novelty_discovery=avg_novelty,
        winner_hotkey=winner_hotkey,
        winner_score=winner_score,
        total_novelty_found=total_novelty if total_novelty > 0 else None,
        baseline_beat_count=baseline_beat_count,
    )

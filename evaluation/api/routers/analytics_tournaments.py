"""
Analytics Tournament router endpoints.

Provides read-only access to Analytics tournament data, submissions,
results, evaluation runs, and miner histories.

API prefix: /api/v1/analytics/tournaments/
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from evaluation.api.dependencies import get_db
from evaluation.api.models.responses import (
    TournamentResponse,
    TournamentDetailResponse,
    SubmissionResponse,
    EvaluationRunResponse,
    TournamentResultResponse,
    LeaderboardResponse,
    LeaderboardEntry,
)
from evaluation.models.database import (
    AnalyticsTournament,
    AnalyticsTournamentSubmission,
    AnalyticsTournamentEvaluationRun,
    AnalyticsTournamentResult,
)


router = APIRouter(prefix="/api/v1/analytics", tags=["Tournaments"])


@router.post(
    "/tournaments/start",
    summary="Start New Tournament",
    description="""
Start a new tournament manually with current configuration.

**Note:** In production with `TOURNAMENT_SCHEDULE_MODE=daily`,
tournaments auto-start at 00:00 UTC via Celery Beat.

This endpoint is primarily for development with `TOURNAMENT_SCHEDULE_MODE=manual`.
    """,
    response_model=dict,
)
async def start_tournament(
    epoch_number: int = Query(..., description="Epoch number for this tournament", ge=1),
    db: Session = Depends(get_db),
):
    """Manually trigger a new tournament"""
    from evaluation.tasks.epoch_start_task import epoch_start_task
    
    # Check for active tournament
    active = db.query(AnalyticsTournament).filter(
        AnalyticsTournament.status.in_([
            "pending",
            "collecting",
            "testing",
            "evaluating"
        ])
    ).first()
    
    if active:
        raise HTTPException(
            status_code=409,
            detail=f"Active tournament exists: epoch {active.epoch_number}, status={active.status}"
        )
    
    # Check if epoch already exists
    existing = db.query(AnalyticsTournament).filter(
        AnalyticsTournament.epoch_number == epoch_number
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Tournament for epoch {epoch_number} already exists"
        )
    
    # Trigger task
    task = epoch_start_task.delay(epoch_number)
    
    return {
        "task_id": task.id,
        "epoch_number": epoch_number,
        "message": "Tournament starting",
        "status": "queued"
    }


@router.get(
    "/tournaments",
    response_model=list[TournamentResponse],
    summary="List Tournaments",
    description="""
Retrieve a paginated list of Analytics tournaments.

Analytics tournaments evaluate miners on pattern detection and feature
generation using synthetic blockchain data.

### Three Evaluation Pillars
1. **Features**: Schema validation and generation performance (10%)
2. **Synthetic Patterns**: Recall of known patterns from ground_truth (30%)
3. **Novelty Patterns**: Discovery of new valid patterns via flow tracing (25%)
4. **Precision**: Anti-cheat - penalizes fake patterns (25%)
5. **Performance**: Detection speed (10%)

### Filtering
- **status**: pending, in_progress, evaluating, completed, failed
- **epoch_number**: Filter by specific epoch

### Pagination
Use `limit` and `offset` for pagination (max 100 per request).
    """,
    response_description="List of tournaments",
    responses={
        200: {
            "description": "Successfully retrieved tournament list",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "epoch_number": 8,
                            "status": "completed",
                            "started_at": "2025-01-09T00:00:00Z",
                            "completed_at": "2025-01-09T23:59:59Z",
                            "total_submissions": 45,
                            "total_evaluation_runs": 180,
                            "test_networks": ["torus"],
                            "baseline_repository": "https://github.com/subnet/baseline",
                            "baseline_version": "v2.1.0",
                            "created_at": "2025-01-09T00:00:00Z"
                        }
                    ]
                }
            }
        }
    },
)
async def list_tournaments(
    status: Optional[str] = Query(
        None,
        description="Filter by status (pending, in_progress, evaluating, completed, failed)",
        examples=["completed"],
    ),
    epoch_number: Optional[int] = Query(
        None,
        description="Filter by epoch number",
        examples=[8],
    ),
    limit: int = Query(
        default=50,
        le=100,
        description="Maximum tournaments to return (max 100)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number to skip for pagination",
    ),
    db: Session = Depends(get_db),
):
    """
    List tournaments with optional filtering.
    
    Returns tournament summary with submission and run counts.
    Sorted by creation date (newest first).
    """
    query = db.query(AnalyticsTournament)
    
    if status:
        query = query.filter(AnalyticsTournament.status == status)
    if epoch_number is not None:
        query = query.filter(AnalyticsTournament.epoch_number == epoch_number)
    
    tournaments = query.order_by(AnalyticsTournament.created_at.desc()).offset(offset).limit(limit).all()
    
    return [
        TournamentResponse(
            id=str(t.id),
            epoch_number=t.epoch_number,
            status=t.status,
            started_at=t.started_at,
            completed_at=t.completed_at,
            total_submissions=t.total_submissions or 0,
            total_evaluation_runs=t.total_evaluation_runs or 0,
            test_networks=t.test_networks or [],
            baseline_repository=t.baseline_repository,
            baseline_version=t.baseline_version,
            created_at=t.created_at,
        )
        for t in tournaments
    ]


@router.get(
    "/tournaments/{tournament_id}",
    response_model=TournamentDetailResponse,
    summary="Get Tournament Details",
    description="""
Retrieve complete details for a specific tournament.

Returns full tournament information including:
- Tournament configuration and status
- All miner submissions
- Final results/leaderboard (if completed)

Use for tournament detail pages.
    """,
    response_description="Complete tournament details",
    responses={
        200: {"description": "Successfully retrieved tournament details"},
        404: {"description": "Tournament not found"},
    },
)
async def get_tournament(
    tournament_id: UUID,
    db: Session = Depends(get_db),
):
    """Get detailed information for a single tournament."""
    tournament = db.query(AnalyticsTournament).filter(
        AnalyticsTournament.id == tournament_id
    ).first()
    
    if not tournament:
        raise HTTPException(status_code=404, detail="tournament_not_found")
    
    submissions = [
        SubmissionResponse(
            id=str(s.id),
            tournament_id=str(s.tournament_id),
            hotkey=s.hotkey,
            uid=s.uid,
            docker_image_digest=s.docker_image_digest,
            repository_url=s.repository_url,
            status=s.status,
            validation_error=s.validation_error,
            submitted_at=s.submitted_at,
            validated_at=s.validated_at,
        )
        for s in tournament.submissions
    ]
    
    results = [
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
        for r in sorted(tournament.results, key=lambda x: x.rank)
    ]
    
    return TournamentDetailResponse(
        id=str(tournament.id),
        epoch_number=tournament.epoch_number,
        status=tournament.status,
        started_at=tournament.started_at,
        completed_at=tournament.completed_at,
        total_submissions=tournament.total_submissions or 0,
        total_evaluation_runs=tournament.total_evaluation_runs or 0,
        test_networks=tournament.test_networks or [],
        baseline_repository=tournament.baseline_repository,
        baseline_version=tournament.baseline_version,
        created_at=tournament.created_at,
        submissions=submissions,
        results=results,
    )


@router.get(
    "/tournaments/{tournament_id}/leaderboard",
    response_model=LeaderboardResponse,
    summary="Get Tournament Leaderboard",
    description="""
Retrieve the leaderboard for a tournament.

Returns ranked list of participants with key scoring metrics:
- Final weighted score
- Synthetic recall (ground_truth detection)
- Pattern precision (anti-cheat)
- Novelty discovery score

Sorted by rank (best first).
    """,
    response_description="Tournament leaderboard with rankings",
    responses={
        200: {"description": "Successfully retrieved leaderboard"},
        404: {"description": "Tournament not found"},
    },
)
async def get_tournament_leaderboard(
    tournament_id: UUID,
    db: Session = Depends(get_db),
):
    """Get the leaderboard for a tournament."""
    tournament = db.query(AnalyticsTournament).filter(
        AnalyticsTournament.id == tournament_id
    ).first()
    
    if not tournament:
        raise HTTPException(status_code=404, detail="tournament_not_found")
    
    results = db.query(AnalyticsTournamentResult).filter(
        AnalyticsTournamentResult.tournament_id == tournament_id
    ).order_by(AnalyticsTournamentResult.rank).all()
    
    entries = [
        LeaderboardEntry(
            rank=r.rank,
            hotkey=r.hotkey,
            uid=r.uid,
            final_score=r.final_score,
            synthetic_recall_score=r.synthetic_recall_score,
            pattern_precision_score=r.pattern_precision_score,
            novelty_discovery_score=r.novelty_discovery_score,
            beat_baseline=r.beat_baseline,
        )
        for r in results
    ]
    
    baseline_beat_count = sum(1 for r in results if r.beat_baseline)
    
    return LeaderboardResponse(
        tournament_id=str(tournament_id),
        epoch_number=tournament.epoch_number,
        status=tournament.status,
        entries=entries,
        total_participants=len(results),
        baseline_beat_count=baseline_beat_count,
    )


@router.get(
    "/tournaments/{tournament_id}/results",
    response_model=list[TournamentResultResponse],
    summary="Get Tournament Results",
    description="""
Retrieve detailed results for all participants in a tournament.

Each result includes:
- Gate pass rates (schema validity, pattern existence)
- Component scores (feature perf, synthetic recall, precision, novelty, pattern perf)
- Aggregate totals (patterns reported, synthetic found, novelty valid/invalid)
- Final score, rank, and baseline comparison

Sorted by rank (best first).
    """,
    response_description="Detailed tournament results",
    responses={
        200: {"description": "Successfully retrieved results"},
    },
)
async def get_tournament_results(
    tournament_id: UUID,
    db: Session = Depends(get_db),
):
    """Get detailed results for a tournament."""
    results = db.query(AnalyticsTournamentResult).filter(
        AnalyticsTournamentResult.tournament_id == tournament_id
    ).order_by(AnalyticsTournamentResult.rank).all()
    
    return [
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
        for r in results
    ]


@router.get(
    "/tournaments/{tournament_id}/submissions",
    response_model=list[SubmissionResponse],
    summary="List Tournament Submissions",
    description="""
Retrieve all miner submissions for a tournament.

Returns Docker image references and validation status.
Sorted by submission time (newest first).

### Filtering
- **status**: pending, validating, valid, invalid
    """,
    response_description="List of submissions",
    responses={
        200: {"description": "Successfully retrieved submissions"},
    },
)
async def get_tournament_submissions(
    tournament_id: UUID,
    status: Optional[str] = Query(
        None,
        description="Filter by status (pending, validating, valid, invalid)",
        examples=["valid"],
    ),
    db: Session = Depends(get_db),
):
    """List all submissions for a tournament."""
    query = db.query(AnalyticsTournamentSubmission).filter(
        AnalyticsTournamentSubmission.tournament_id == tournament_id
    )
    
    if status:
        query = query.filter(AnalyticsTournamentSubmission.status == status)
    
    submissions = query.order_by(
        AnalyticsTournamentSubmission.submitted_at.desc()
    ).all()
    
    return [
        SubmissionResponse(
            id=str(s.id),
            tournament_id=str(s.tournament_id),
            hotkey=s.hotkey,
            uid=s.uid,
            docker_image_digest=s.docker_image_digest,
            repository_url=s.repository_url,
            status=s.status,
            validation_error=s.validation_error,
            submitted_at=s.submitted_at,
            validated_at=s.validated_at,
        )
        for s in submissions
    ]


@router.get(
    "/tournaments/{tournament_id}/runs",
    response_model=list[EvaluationRunResponse],
    summary="List Evaluation Runs",
    description="""
Retrieve evaluation runs for a tournament.

Each run contains detailed scoring breakdown:
- Gate results (schema valid, pattern existence)
- Synthetic pattern detection (expected vs found)
- Novelty pattern discovery (valid vs invalid)
- All 5 component scores
- Final weighted score

### Filtering
- **epoch_number**: Filter by epoch
- **network**: Filter by test network
- **status**: pending, running, completed, failed, timeout
- **hotkey**: Filter by specific miner

### Pagination
Max 500 runs per request.
    """,
    response_description="List of evaluation runs with detailed scores",
    responses={
        200: {"description": "Successfully retrieved runs"},
    },
)
async def get_tournament_runs(
    tournament_id: UUID,
    epoch_number: Optional[int] = Query(None, description="Filter by epoch"),
    network: Optional[str] = Query(None, description="Filter by network"),
    status: Optional[str] = Query(None, description="Filter by status"),
    hotkey: Optional[str] = Query(None, description="Filter by miner hotkey"),
    limit: int = Query(default=100, le=500, description="Max runs to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
):
    """List evaluation runs for a tournament."""
    query = db.query(
        AnalyticsTournamentEvaluationRun,
        AnalyticsTournamentSubmission.hotkey
    ).join(AnalyticsTournamentSubmission).filter(
        AnalyticsTournamentSubmission.tournament_id == tournament_id
    )
    
    if epoch_number is not None:
        query = query.filter(AnalyticsTournamentEvaluationRun.epoch_number == epoch_number)
    if network:
        query = query.filter(AnalyticsTournamentEvaluationRun.network == network)
    if status:
        query = query.filter(AnalyticsTournamentEvaluationRun.status == status)
    if hotkey:
        query = query.filter(AnalyticsTournamentSubmission.hotkey == hotkey)
    
    runs = query.order_by(
        AnalyticsTournamentEvaluationRun.started_at.desc()
    ).offset(offset).limit(limit).all()
    
    return [
        EvaluationRunResponse(
            id=str(run.id),
            submission_id=str(run.submission_id),
            hotkey=hk,
            epoch_number=run.epoch_number,
            network=run.network,
            test_date=run.test_date,
            status=run.status,
            output_schema_valid=run.output_schema_valid,
            feature_generation_time_seconds=run.feature_generation_time_seconds,
            pattern_existence=run.pattern_existence,
            patterns_reported=run.patterns_reported,
            synthetic_addresses_expected=run.synthetic_addresses_expected,
            synthetic_addresses_found=run.synthetic_addresses_found,
            novelty_patterns_valid=run.novelty_patterns_valid,
            novelty_patterns_invalid=run.novelty_patterns_invalid,
            pattern_detection_time_seconds=run.pattern_detection_time_seconds,
            feature_performance_score=run.feature_performance_score,
            synthetic_recall_score=run.synthetic_recall_score,
            pattern_precision_score=run.pattern_precision_score,
            novelty_discovery_score=run.novelty_discovery_score,
            pattern_performance_score=run.pattern_performance_score,
            final_score=run.final_score,
            exit_code=run.exit_code,
            started_at=run.started_at,
            completed_at=run.completed_at,
            error_message=run.error_message,
        )
        for run, hk in runs
    ]

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
    MinerHistoryResponse,
    MinerTournamentEntry,
)
from evaluation.models.database import Tournament, Submission, EvaluationRun, TournamentResult


router = APIRouter(prefix="/api/v1", tags=["tournaments"])


@router.get("/tournaments", response_model=list[TournamentResponse])
async def list_tournaments(
    status: Optional[str] = Query(None, description="Filter by status"),
    netuid: Optional[int] = Query(None, description="Filter by netuid"),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(Tournament)
    
    if status:
        query = query.filter(Tournament.status == status)
    if netuid:
        query = query.filter(Tournament.netuid == netuid)
    
    tournaments = query.order_by(Tournament.created_at.desc()).offset(offset).limit(limit).all()
    
    result = []
    for t in tournaments:
        submission_count = db.query(func.count(Submission.id)).filter(
            Submission.tournament_id == t.id
        ).scalar()
        
        result.append(TournamentResponse(
            id=str(t.id),
            name=t.name,
            netuid=t.netuid,
            status=t.status,
            registration_start=t.registration_start,
            registration_end=t.registration_end,
            start_block=t.start_block,
            end_block=t.end_block,
            epoch_blocks=t.epoch_blocks,
            test_networks=t.test_networks,
            baseline_repository=t.baseline_repository,
            baseline_version=t.baseline_version,
            created_at=t.created_at,
            completed_at=t.completed_at,
            submission_count=submission_count
        ))
    
    return result


@router.get("/tournaments/{tournament_id}", response_model=TournamentDetailResponse)
async def get_tournament(
    tournament_id: UUID,
    db: Session = Depends(get_db)
):
    tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="tournament_not_found")
    
    submissions = []
    for s in tournament.submissions:
        run_count = db.query(func.count(EvaluationRun.id)).filter(
            EvaluationRun.submission_id == s.id
        ).scalar()
        
        submissions.append(SubmissionResponse(
            id=str(s.id),
            tournament_id=str(s.tournament_id),
            hotkey=s.hotkey,
            uid=s.uid,
            repository_url=s.repository_url,
            commit_hash=s.commit_hash,
            docker_image_tag=s.docker_image_tag,
            status=s.status,
            validation_error=s.validation_error,
            submitted_at=s.submitted_at,
            validated_at=s.validated_at,
            run_count=run_count
        ))
    
    results = [
        TournamentResultResponse(
            id=str(r.id),
            tournament_id=str(r.tournament_id),
            hotkey=r.hotkey,
            uid=r.uid,
            pattern_accuracy_score=r.pattern_accuracy_score,
            data_correctness_score=r.data_correctness_score,
            performance_score=r.performance_score,
            final_score=r.final_score,
            rank=r.rank,
            beat_baseline=r.beat_baseline,
            is_winner=r.is_winner,
            calculated_at=r.calculated_at
        )
        for r in sorted(tournament.results, key=lambda x: x.rank)
    ]
    
    return TournamentDetailResponse(
        id=str(tournament.id),
        name=tournament.name,
        netuid=tournament.netuid,
        status=tournament.status,
        registration_start=tournament.registration_start,
        registration_end=tournament.registration_end,
        start_block=tournament.start_block,
        end_block=tournament.end_block,
        epoch_blocks=tournament.epoch_blocks,
        test_networks=tournament.test_networks,
        baseline_repository=tournament.baseline_repository,
        baseline_version=tournament.baseline_version,
        created_at=tournament.created_at,
        completed_at=tournament.completed_at,
        submissions=submissions,
        results=results
    )


@router.get("/tournaments/{tournament_id}/submissions", response_model=list[SubmissionResponse])
async def get_tournament_submissions(
    tournament_id: UUID,
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Submission).filter(Submission.tournament_id == tournament_id)
    
    if status:
        query = query.filter(Submission.status == status)
    
    submissions = query.order_by(Submission.submitted_at.desc()).all()
    
    result = []
    for s in submissions:
        run_count = db.query(func.count(EvaluationRun.id)).filter(
            EvaluationRun.submission_id == s.id
        ).scalar()
        
        result.append(SubmissionResponse(
            id=str(s.id),
            tournament_id=str(s.tournament_id),
            hotkey=s.hotkey,
            uid=s.uid,
            repository_url=s.repository_url,
            commit_hash=s.commit_hash,
            docker_image_tag=s.docker_image_tag,
            status=s.status,
            validation_error=s.validation_error,
            submitted_at=s.submitted_at,
            validated_at=s.validated_at,
            run_count=run_count
        ))
    
    return result


@router.get("/tournaments/{tournament_id}/results", response_model=list[TournamentResultResponse])
async def get_tournament_results(
    tournament_id: UUID,
    db: Session = Depends(get_db)
):
    results = db.query(TournamentResult).filter(
        TournamentResult.tournament_id == tournament_id
    ).order_by(TournamentResult.rank).all()
    
    return [
        TournamentResultResponse(
            id=str(r.id),
            tournament_id=str(r.tournament_id),
            hotkey=r.hotkey,
            uid=r.uid,
            pattern_accuracy_score=r.pattern_accuracy_score,
            data_correctness_score=r.data_correctness_score,
            performance_score=r.performance_score,
            final_score=r.final_score,
            rank=r.rank,
            beat_baseline=r.beat_baseline,
            is_winner=r.is_winner,
            calculated_at=r.calculated_at
        )
        for r in results
    ]


@router.get("/tournaments/{tournament_id}/runs", response_model=list[EvaluationRunResponse])
async def get_tournament_runs(
    tournament_id: UUID,
    epoch_number: Optional[int] = Query(None),
    network: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(EvaluationRun, Submission.hotkey).join(Submission).filter(
        Submission.tournament_id == tournament_id
    )
    
    if epoch_number is not None:
        query = query.filter(EvaluationRun.epoch_number == epoch_number)
    if network:
        query = query.filter(EvaluationRun.network == network)
    if status:
        query = query.filter(EvaluationRun.status == status)
    
    runs = query.order_by(EvaluationRun.started_at.desc()).offset(offset).limit(limit).all()
    
    return [
        EvaluationRunResponse(
            id=str(run.id),
            submission_id=str(run.submission_id),
            hotkey=hotkey,
            epoch_number=run.epoch_number,
            network=run.network,
            test_date=run.test_date,
            status=run.status,
            execution_time_seconds=run.execution_time_seconds,
            exit_code=run.exit_code,
            pattern_recall=run.pattern_recall,
            data_correctness=run.data_correctness,
            started_at=run.started_at,
            completed_at=run.completed_at,
            error_message=run.error_message
        )
        for run, hotkey in runs
    ]


@router.get("/miners/{hotkey}/history", response_model=MinerHistoryResponse)
async def get_miner_history(
    hotkey: str,
    db: Session = Depends(get_db)
):
    submissions = db.query(Submission).filter(
        Submission.hotkey == hotkey
    ).order_by(Submission.submitted_at.desc()).all()
    
    if not submissions:
        raise HTTPException(status_code=404, detail="miner_not_found")
    
    tournament_ids = [s.tournament_id for s in submissions]
    tournaments = {
        t.id: t for t in db.query(Tournament).filter(Tournament.id.in_(tournament_ids)).all()
    }
    
    results = {
        r.tournament_id: r for r in db.query(TournamentResult).filter(
            TournamentResult.hotkey == hotkey
        ).all()
    }
    
    total_wins = 0
    total_baseline_beats = 0
    ranks = []
    entries = []
    
    for s in submissions:
        t = tournaments.get(s.tournament_id)
        r = results.get(s.tournament_id)
        
        rank = r.rank if r else None
        final_score = r.final_score if r else None
        beat_baseline = r.beat_baseline if r else False
        is_winner = r.is_winner if r else False
        
        if is_winner:
            total_wins += 1
        if beat_baseline:
            total_baseline_beats += 1
        if rank:
            ranks.append(rank)
        
        entries.append(MinerTournamentEntry(
            tournament_id=str(s.tournament_id),
            tournament_name=t.name if t else "Unknown",
            status=t.status if t else "unknown",
            rank=rank,
            final_score=final_score,
            beat_baseline=beat_baseline,
            is_winner=is_winner,
            submitted_at=s.submitted_at
        ))
    
    avg_rank = sum(ranks) / len(ranks) if ranks else None
    best_rank = min(ranks) if ranks else None
    
    return MinerHistoryResponse(
        hotkey=hotkey,
        total_tournaments=len(submissions),
        total_wins=total_wins,
        total_baseline_beats=total_baseline_beats,
        average_rank=avg_rank,
        best_rank=best_rank,
        tournaments=entries
    )

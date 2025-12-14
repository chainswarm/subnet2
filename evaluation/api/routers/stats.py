from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from evaluation.api.dependencies import get_db
from evaluation.api.models.responses import StatsResponse
from evaluation.models.database import Tournament, Submission, EvaluationRun, TournamentResult


router = APIRouter(prefix="/api/v1", tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    active_tournaments = db.query(func.count(Tournament.id)).filter(
        Tournament.status.in_(["registration", "active"])
    ).scalar()
    
    completed_tournaments = db.query(func.count(Tournament.id)).filter(
        Tournament.status == "completed"
    ).scalar()
    
    total_miners = db.query(func.count(func.distinct(Submission.hotkey))).scalar()
    
    total_submissions = db.query(func.count(Submission.id)).scalar()
    
    total_runs_completed = db.query(func.count(EvaluationRun.id)).filter(
        EvaluationRun.status == "completed"
    ).scalar()
    
    avg_recall = db.query(func.avg(EvaluationRun.pattern_recall)).filter(
        EvaluationRun.pattern_recall.isnot(None)
    ).scalar()
    
    total_results = db.query(func.count(TournamentResult.id)).scalar()
    baseline_beats = db.query(func.count(TournamentResult.id)).filter(
        TournamentResult.beat_baseline == True
    ).scalar()
    
    baseline_beat_rate = None
    if total_results > 0:
        baseline_beat_rate = baseline_beats / total_results
    
    return StatsResponse(
        active_tournaments=active_tournaments or 0,
        completed_tournaments=completed_tournaments or 0,
        total_miners=total_miners or 0,
        total_submissions=total_submissions or 0,
        total_runs_completed=total_runs_completed or 0,
        average_pattern_recall=float(avg_recall) if avg_recall else None,
        baseline_beat_rate=baseline_beat_rate
    )

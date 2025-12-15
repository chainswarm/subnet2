import time
from uuid import UUID
from loguru import logger

from evaluation.db import get_session
from evaluation.repositories.tournament_repository import TournamentRepository
from evaluation.tasks.celery_app import celery_app


@celery_app.task(name="evaluation.orchestrate_tournament")
def orchestrate_tournament_task(tournament_id: str) -> dict:
    """
    Orchestrate the complete tournament lifecycle:
    1. Wait for submission duration
    2. For each epoch: trigger evaluations and wait
    3. Trigger final ranking and weight setting
    
    Args:
        tournament_id: UUID of the tournament to orchestrate
        
    Returns:
        Dict with execution summary
    """
    session = get_session()
    repo = TournamentRepository(session)
    
    try:
        tournament = repo.get_by_id(UUID(tournament_id))
        if not tournament:
            raise ValueError(f"tournament_not_found: {tournament_id}")
        
        # Get configuration
        submission_duration = tournament.config.get("submission_duration_seconds", 120)
        epoch_count = tournament.config.get("epoch_count", 3)
        epoch_duration = tournament.config.get("epoch_duration_seconds", 180)
        
        logger.info(
            "orchestrator_started",
            tournament_id=tournament_id,
            submission_duration=submission_duration,
            epoch_count=epoch_count,
            epoch_duration=epoch_duration,
        )
        
        # Phase 1: Wait for submission duration
        logger.info("waiting_for_submissions", duration=submission_duration)
        time.sleep(submission_duration)
        
        # Phase 2: Testing epochs
        repo.update_status(UUID(tournament_id), "testing")
        
        from evaluation.tasks.evaluation_task import run_epoch_evaluations_task
        
        for epoch_number in range(epoch_count):
            logger.info("starting_epoch", epoch=epoch_number, tournament_id=tournament_id)
            
            # Trigger evaluation for this epoch
            result = run_epoch_evaluations_task.apply_async(
                args=[tournament_id, epoch_number]
            ).get()  # Wait for completion
            
            logger.info(
                "epoch_completed",
                epoch=epoch_number,
                runs_queued=result.get("total_runs_queued", 0),
            )
            
            # Wait between epochs (except after last epoch)
            if epoch_number < epoch_count - 1:
                logger.info("waiting_between_epochs", duration=epoch_duration)
                time.sleep(epoch_duration)
        
        # Phase 3: Final ranking and weight setting
        logger.info("starting_finalization", tournament_id=tournament_id)
        
        from evaluation.tasks.epoch_end_task import epoch_end_task
        end_result = epoch_end_task.apply_async(
            args=[tournament_id]
        ).get()
        
        logger.info(
            "tournament_orchestration_complete",
            tournament_id=tournament_id,
            participants=end_result.get("participants", 0),
            winner=end_result.get("winner"),
        )
        
        return {
            "success": True,
            "tournament_id": tournament_id,
            "epochs_completed": epoch_count,
            "finalization_result": end_result,
        }
    
    except Exception as e:
        logger.error("orchestration_error", tournament_id=tournament_id, error=str(e))
        
        # Mark tournament as failed
        try:
            repo.update_status(UUID(tournament_id), "failed")
        except:
            pass
        
        return {
            "success": False,
            "tournament_id": tournament_id,
            "error": str(e),
        }
    
    finally:
        session.close()

from loguru import logger

from evaluation.tasks.celery_app import celery_app


@celery_app.task(name="evaluation.epoch_start")
def epoch_start_task(epoch_number: int = None) -> str:
    """
    DEPRECATED: Tournament submission collection now handled by validator.
    
    This task is kept for backward compatibility but does nothing.
    The validator's forward() loop handles submission collection.
    """
    logger.warning("epoch_start_task called but is deprecated - validator handles submission collection")
    return None

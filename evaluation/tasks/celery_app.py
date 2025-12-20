from chainswarm_core.jobs import create_celery_app
from config import config

celery_app = create_celery_app(
    name="subnet-evaluation",
    autodiscover=["evaluation.tasks"],
    beat_schedule_path="evaluation/tasks/beat_schedule.json" if config.tournament_schedule_mode == "daily" else None,
    broker_url=config.redis_url,
    result_backend=config.redis_url,
    task_time_limit=3600,
    task_soft_time_limit=3500,
)

from celery import Celery

from config import config

celery_app = Celery(
    "subnet2_evaluation",
    broker=config.redis_url,
    backend=config.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3500,
)

celery_app.autodiscover_tasks([
    "evaluation.tasks",
])

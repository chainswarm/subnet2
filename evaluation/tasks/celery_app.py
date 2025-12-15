import json
from pathlib import Path

from celery import Celery
from celery.schedules import crontab

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

# Load beat schedule from JSON if in daily mode
if config.tournament_schedule_mode == "daily":
    beat_schedule_path = Path(__file__).parent / "beat_schedule.json"
    if beat_schedule_path.exists():
        with open(beat_schedule_path) as f:
            schedule_config = json.load(f)
            
        # Convert cron strings to crontab objects
        beat_schedule = {}
        for name, task_config in schedule_config.items():
            cron_parts = task_config["schedule"].split()
            beat_schedule[name] = {
                "task": task_config["task"],
                "schedule": crontab(
                    minute=cron_parts[0],
                    hour=cron_parts[1],
                    day_of_month=cron_parts[2],
                    month_of_year=cron_parts[3],
                    day_of_week=cron_parts[4],
                ),
                "args": task_config.get("args", []),
            }
        
        celery_app.conf.beat_schedule = beat_schedule

celery_app.autodiscover_tasks([
    "evaluation.tasks",
])

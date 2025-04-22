from celery import Celery
from app.core.config import settings

# Initialize Celery
celery_app = Celery(
    'store_monitoring',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.services.report_service']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  
    worker_max_tasks_per_child=1,
    broker_connection_retry_on_startup=True,
    # Windows-specific settings
    worker_pool='solo',  # Use solo pool for Windows compatibility
    worker_pool_restarts=True
) 
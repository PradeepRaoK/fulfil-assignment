from celery import Celery
import os


CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

celery = Celery('app', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)
celery.autodiscover_tasks(["app.tasks"])
celery.conf.task_track_started = True
celery.conf.task_serializer = "json"
celery.conf.result_serializer = "json"
celery.conf.accept_content = ["json"]
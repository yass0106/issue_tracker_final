import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

app = Celery('project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

from celery.schedules import crontab

app.conf.beat_schedule = {
    'mark-overdue-every-hour': {
        'task': 'app.tasks.mark_overdue_issues',
        'schedule': crontab(minute='*/5', hour='*'),  # every hour
    },
}

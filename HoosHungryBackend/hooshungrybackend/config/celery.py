import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('hooshungry')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Schedule tasks
app.conf.beat_schedule = {
    'scrape-menus-daily': {
        'task': 'api.tasks.scrape_all_menus',
        'schedule': crontab(hour=5, minute=0),  # 5:00 AM daily
    },
}

app.conf.timezone = 'America/New_York'

import fcntl
import os
import tempfile

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone='America/New_York')
_lock_file = None


def scrape_menus_job():
    logger.info("Scheduler triggered: running scrape_menus")
    call_command('scrape_menus')


def start():
    global _lock_file
    if scheduler.running:
        return
    # Use a file lock so only one gunicorn worker starts the scheduler
    lock_path = os.path.join(tempfile.gettempdir(), 'scheduler.lock')
    _lock_file = open(lock_path, 'w')
    try:
        fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        _lock_file.close()
        _lock_file = None
        logger.info("Scheduler already running in another worker, skipping")
        return
    scheduler.add_job(
        scrape_menus_job,
        trigger=CronTrigger(hour=0, minute=0),
        id='scrape_menus_daily',
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started: scrape_menus scheduled daily at 12:00 AM ET")

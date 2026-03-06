from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone='America/New_York')


def scrape_menus_job():
    logger.info("Scheduler triggered: running scrape_menus")
    call_command('scrape_menus')


def start():
    if scheduler.running:
        return
    scheduler.add_job(
        scrape_menus_job,
        trigger=CronTrigger(hour=5, minute=0),
        id='scrape_menus_daily',
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started: scrape_menus scheduled daily at 5:00 AM ET")

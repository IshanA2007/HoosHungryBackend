from celery import shared_task
from .scrapers import get_menu_data, get_hours
from .importers import load_menu_data
import logging

logger = logging.getLogger(__name__)

@shared_task(name='api.tasks.scrape_all_menus')
def scrape_all_menus():
    """Scrape menu data for all dining halls"""
    halls = ['ohill', 'newcomb', 'runk']
    results = {}
    
    logger.info("Starting daily menu scrape...")
    
    for hall in halls:
        try:
            logger.info(f"Scraping {hall}...")
            menu_data = get_menu_data(hall)
            hours_data = get_hours(hall)
            load_menu_data(hall, menu_data, hours_data)
            results[hall] = "success"
            logger.info(f"✓ Successfully scraped {hall}")
        except Exception as e:
            results[hall] = f"error: {str(e)}"
            logger.error(f"✗ Error scraping {hall}: {str(e)}")
    
    logger.info(f"Daily scrape completed. Results: {results}")
    return results

@shared_task(name='api.tasks.scrape_single_hall')
def scrape_single_hall(hall_name):
    """Scrape menu data for a single dining hall"""
    try:
        logger.info(f"Scraping {hall_name}...")
        menu_data = get_menu_data(hall_name)
        hours_data = get_hours(hall_name)
        load_menu_data(hall_name, menu_data, hours_data)
        logger.info(f"✓ Successfully scraped {hall_name}")
        return f"Successfully scraped {hall_name}"
    except Exception as e:
        logger.error(f"✗ Error scraping {hall_name}: {str(e)}")
        raise
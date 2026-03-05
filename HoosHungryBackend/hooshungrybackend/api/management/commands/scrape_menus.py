from django.core.management.base import BaseCommand
from api.scrapers import get_menu_data, get_hours
from api.importers import load_menu_data
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Scrape menu data for all dining halls (or a single hall)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hall',
            type=str,
            help='Scrape a single hall (ohill, newcomb, or runk)',
        )

    def handle(self, *args, **options):
        hall = options.get('hall')
        halls = [hall] if hall else ['ohill', 'newcomb', 'runk']
        results = {}

        logger.info("Starting menu scrape...")

        for h in halls:
            try:
                logger.info(f"Scraping {h}...")
                menu_data = get_menu_data(h)
                hours_data = get_hours(h)
                load_menu_data(h, menu_data, hours_data)
                results[h] = "success"
                self.stdout.write(self.style.SUCCESS(f"Successfully scraped {h}"))
            except Exception as e:
                results[h] = f"error: {str(e)}"
                self.stderr.write(self.style.ERROR(f"Error scraping {h}: {str(e)}"))

        logger.info(f"Scrape completed. Results: {results}")

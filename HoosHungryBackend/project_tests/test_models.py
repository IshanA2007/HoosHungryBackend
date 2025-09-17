import datetime
from django.test import TestCase
from api.models import DiningHall, Day, Period, Station, MenuItem, Allergen, Ingredient, NutritionInfo

class DiningModelsTest(TestCase):

    def setUp(self):
        # Create a DiningHall
        self.hall = DiningHall.objects.create(
            name="Newcomb Dining Hall",
            scrape_url="http://example.com/menu"
        )

        # Create a Day
        self.day = Day.objects.create(
            date=datetime.date(2025, 9, 16),
            day_name="Tuesday",
            open_time=datetime.time(7, 0),
            close_time=datetime.time(20, 0),
            dining_hall=self.hall
        )

        # Create a Period
        self.period = Period.objects.create(
            type="Lunch",
            vendor_id="1423",
            start_time=datetime.time(11, 0),
            end_time=datetime.time(14, 0),
            day=self.day
        )

        # Create a Station
        self.station = Station.objects.create(
            name="Grill",
            number="22683",
            period=self.period
        )

        # Create Ingredients + Allergens
        self.peanut = Allergen.objects.create(name="Peanuts")
        self.wheat = Allergen.objects.create(name="Wheat")
        self.tomato = Ingredient.objects.create(name="Tomato")

        # Create NutritionInfo
        self.nutrition = NutritionInfo.objects.create(
            calories=350,
            protein=20,
            carbs=30,
            sugar=5,
            sodium=500
        )

        # Create a MenuItem
        self.item = MenuItem.objects.create(
            station=self.station,
            item_name="Peanut Butter Sandwich",
            is_gluten=True,
            is_vegetarian=True,
            nutrition_info=self.nutrition
        )
        self.item.allergens.add(self.peanut, self.wheat)
        self.item.ingredients.add(self.tomato)

    def test_dininghall_has_days(self):
        self.assertEqual(self.hall.days.count(), 1)
        self.assertEqual(self.hall.days.first(), self.day)

    def test_day_has_periods(self):
        self.assertEqual(self.day.periods.count(), 1)
        self.assertEqual(self.day.periods.first(), self.period)

    def test_station_has_menuitems(self):
        self.assertEqual(self.station.menu_items.count(), 1)
        self.assertEqual(self.station.menu_items.first(), self.item)

    def test_menuitem_allergens(self):
        allergen_names = list(self.item.allergens.values_list("name", flat=True))
        self.assertIn("Peanuts", allergen_names)
        self.assertIn("Wheat", allergen_names)

    def test_menuitem_nutrition(self):
        self.assertEqual(self.item.nutrition_info.calories, 350)
        self.assertEqual(self.item.nutrition_info.protein, 20)
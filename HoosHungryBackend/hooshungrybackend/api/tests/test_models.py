import datetime
from django.test import TestCase
from api.models import (
    DiningHall, Day, Period, Station,
    MenuItem, Allergen, Ingredient, NutritionInfo
)

class DiningModelsTest(TestCase):
    def setUp(self):
        # DiningHall
        self.hall = DiningHall.objects.create(
            name="Newcomb Dining Hall",
            scrape_url="http://example.com/menu",
        )

        # Day (no day_name arg)
        self.day = Day.objects.create(
            date=datetime.date(2025, 9, 16),
            day_name="Tuesday",
            open_time=datetime.time(7, 0),
            close_time=datetime.time(20, 0),
            dining_hall=self.hall,
        )

        # Period
        self.period = Period.objects.create(
            type="Lunch",
            vendor_id="1423",
            start_time=datetime.time(11, 0),
            end_time=datetime.time(14, 0),
            day=self.day,
        )

        # Station
        self.station = Station.objects.create(
            name="Grill",
            number="22683",
            period=self.period,
        )

        # Ingredients + Allergens
        self.peanut = Allergen.objects.create(name="Peanuts")
        self.wheat = Allergen.objects.create(name="Wheat")
        self.tomato = Ingredient.objects.create(name="Tomato")

        # MenuItem FIRST
        self.item = MenuItem.objects.create(
            station=self.station,
            item_name="Peanut Butter Sandwich",
            is_gluten=True,
            is_vegetarian=True,
        )
        self.item.allergens.add(self.peanut, self.wheat)
        self.item.ingredients.add(self.tomato)

        # Then attach NutritionInfo to that item
        self.nutrition = NutritionInfo.objects.create(
            menu_item=self.item,
            calories=350,
            protein=20,
            carbs=30,
            sugar=5,
            sodium=500,
        )

    def test_dininghall_has_days(self):
        print(self.hall)
        self.assertEqual(self.hall.days.count(), 1)
        self.assertEqual(self.hall.days.first(), self.day)

    def test_day_has_periods(self):
        print(self.day)
        print(self.day.periods.all())
        self.assertEqual(self.day.periods.count(), 1)
        self.assertEqual(self.day.periods.first(), self.period)

    def test_station_has_menuitems(self):
        print(self.station)
        print(self.station.menu_items.all())
        self.assertEqual(self.station.menu_items.count(), 1)
        self.assertEqual(self.station.menu_items.first(), self.item)

    def test_menuitem_allergens(self):
        print(self.item)
        print(self.item.allergens.all())
        allergen_names = set(self.item.allergens.values_list("name", flat=True))
        self.assertEqual(allergen_names, {"Peanuts", "Wheat"})

    def test_menuitem_nutrition(self):
        self.assertEqual(self.item.nutrition_info.calories, 350)
        self.assertEqual(self.item.nutrition_info.protein, 20)

    def test_dininghall_str(self):
        self.assertEqual(str(self.hall), "Newcomb Dining Hall")

    def test_day_str(self):
        # Day.__str__ → "2025-09-16 (07:00 - 20:00)"
        self.assertEqual(str(self.day), "2025-09-16 (07:00 - 20:00)")

    def test_period_str(self):
        # Period.__str__ → "Lunch (11:00 - 14:00)"
        self.assertEqual(str(self.period), "Lunch (11:00 - 14:00)")

    def test_station_str(self):
        self.assertEqual(str(self.station), "Grill")

    def test_menuitem_str(self):
        self.assertEqual(str(self.item), "Peanut Butter Sandwich")

    def test_allergen_str(self):
        self.assertEqual(str(self.peanut), "Peanuts")

    def test_ingredient_str(self):
        self.assertEqual(str(self.tomato), "Tomato")

    def test_nutritioninfo_str(self):
        # depends on which fields are filled
        expected = "Calories: 350, Protein: 20g, Carbs: 30g, Sugar: 5g, Sodium: 500mg"
        self.assertEqual(str(self.item.nutrition_info), expected)

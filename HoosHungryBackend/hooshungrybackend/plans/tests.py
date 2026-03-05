from django.test import TestCase
from django.contrib.auth.models import User
from plans.models import Plan, DailyMealPlan, MealItem
from decimal import Decimal
import datetime

class MealItemNutritionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.plan = Plan.objects.create(
            user=self.user,
            week_start_date=datetime.date(2026, 3, 1),
        )
        self.daily = DailyMealPlan.objects.create(
            plan=self.plan,
            date=datetime.date(2026, 3, 3),
        )

    def test_meal_item_stores_extended_nutrients(self):
        item = MealItem.objects.create(
            daily_plan=self.daily,
            meal_type='lunch',
            menu_item_id=1,
            menu_item_name='Test Food',
            servings=Decimal('2.00'),
            calories_per_serving=200,
            protein_per_serving=Decimal('10.00'),
            carbs_per_serving=Decimal('30.00'),
            fat_per_serving=Decimal('5.00'),
            fiber_per_serving=Decimal('3.00'),
            sodium_per_serving=Decimal('400.00'),
            sugar_per_serving=Decimal('8.00'),
            cholesterol_per_serving=Decimal('15.00'),
            saturated_fat_per_serving=Decimal('2.00'),
            trans_fat_per_serving=Decimal('0.00'),
        )
        self.assertEqual(item.total_fiber, Decimal('6.00'))
        self.assertEqual(item.total_sodium, Decimal('800.00'))
        self.assertEqual(item.total_sugar, Decimal('16.00'))
        self.assertEqual(item.total_cholesterol, Decimal('30.00'))
        self.assertEqual(item.total_saturated_fat, Decimal('4.00'))
        self.assertEqual(item.total_trans_fat, Decimal('0.00'))

    def test_meal_item_handles_null_nutrients(self):
        """Null per-serving values should produce 0.00 totals"""
        item = MealItem.objects.create(
            daily_plan=self.daily,
            meal_type='breakfast',
            menu_item_id=2,
            menu_item_name='Plain Food',
            servings=Decimal('1.00'),
            calories_per_serving=100,
            # All extended nutrients omitted (None)
        )
        self.assertEqual(item.total_fiber, Decimal('0.00'))
        self.assertEqual(item.total_sodium, Decimal('0.00'))
        self.assertEqual(item.total_sugar, Decimal('0.00'))
        self.assertEqual(item.total_cholesterol, Decimal('0.00'))
        self.assertEqual(item.total_saturated_fat, Decimal('0.00'))
        self.assertEqual(item.total_trans_fat, Decimal('0.00'))

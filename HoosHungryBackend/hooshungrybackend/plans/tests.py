from django.test import TestCase
from django.contrib.auth.models import User
from plans.models import Plan, DailyMealPlan, MealItem
from decimal import Decimal
import datetime
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

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


class DailyMealPlanNutritionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user2', password='pass')
        self.plan = Plan.objects.create(
            user=self.user,
            week_start_date=datetime.date(2026, 3, 1),
        )
        self.daily = DailyMealPlan.objects.create(
            plan=self.plan,
            date=datetime.date(2026, 3, 3),
        )

    def test_daily_plan_aggregates_extended_nutrients(self):
        MealItem.objects.create(
            daily_plan=self.daily,
            meal_type='lunch',
            menu_item_id=1,
            menu_item_name='Food A',
            servings=Decimal('1.00'),
            calories_per_serving=300,
            fiber_per_serving=Decimal('4.00'),
            sodium_per_serving=Decimal('500.00'),
        )
        MealItem.objects.create(
            daily_plan=self.daily,
            meal_type='dinner',
            menu_item_id=2,
            menu_item_name='Food B',
            servings=Decimal('1.00'),
            calories_per_serving=200,
            fiber_per_serving=Decimal('2.00'),
            sodium_per_serving=Decimal('300.00'),
        )
        self.daily.refresh_from_db()
        self.assertEqual(self.daily.total_fiber, Decimal('6.00'))
        self.assertEqual(self.daily.total_sodium, Decimal('800.00'))


class PlanFiberSodiumGoalsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user3', password='pass')

    def test_plan_has_fiber_and_sodium_goals(self):
        plan = Plan.objects.create(
            user=self.user,
            week_start_date=datetime.date(2026, 3, 1),
            daily_fiber_goal=25,
            daily_sodium_goal=2300,
        )
        self.assertEqual(plan.daily_fiber_goal, 25)
        self.assertEqual(plan.daily_sodium_goal, 2300)


class PlanHistoryEndpointTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='historyuser', password='pass')
        self.client = APIClient()
        token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        plan = Plan.objects.create(
            user=self.user,
            week_start_date=datetime.date(2026, 3, 1),
        )
        DailyMealPlan.objects.create(
            plan=plan,
            date=datetime.date(2026, 3, 3),
            total_calories=1800,
        )
        DailyMealPlan.objects.create(
            plan=plan,
            date=datetime.date(2026, 3, 4),
            total_calories=2100,
        )

    def test_history_returns_daily_totals(self):
        response = self.client.get('/api/plan/history/', {'days': 30})
        self.assertEqual(response.status_code, 200)
        self.assertIn('history', response.data)
        dates = [entry['date'] for entry in response.data['history']]
        self.assertIn('2026-03-03', dates)
        self.assertIn('2026-03-04', dates)

    def test_history_requires_authentication(self):
        self.client.credentials()  # Remove auth
        response = self.client.get('/api/plan/history/')
        self.assertEqual(response.status_code, 401)


class AddMealItemNutritionTest(TestCase):
    def setUp(self):
        from api.models import MenuItem, NutritionInfo, DiningHall, Day, Period, Station
        self.user = User.objects.create_user(username='adduser', password='pass')
        self.client = APIClient()
        token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Build minimum dining hall chain
        hall = DiningHall.objects.create(name='ohill', scrape_url='http://test.com')
        day = Day.objects.create(
            date=datetime.date(2026, 3, 3),
            day_name='Tuesday',
            open_time=datetime.time(7, 0),
            close_time=datetime.time(21, 0),
            dining_hall=hall,
        )
        period = Period.objects.create(
            name='Lunch', vendor_id='1',
            start_time=datetime.time(11, 0), end_time=datetime.time(14, 0), day=day
        )
        station = Station.objects.create(name='Grill', number='1', period=period)
        self.menu_item = MenuItem.objects.create(
            station=station, item_name='Test Burger',
            is_vegan=False, is_vegetarian=False
        )
        NutritionInfo.objects.create(
            menu_item=self.menu_item,
            calories=Decimal('500'),
            protein=Decimal('30'),
            total_carbohydrates=Decimal('40'),
            total_fat=Decimal('20'),
            dietary_fiber=Decimal('5'),
            sodium=Decimal('800'),
            total_sugars=Decimal('6'),
            cholesterol=Decimal('70'),
            saturated_fat=Decimal('8'),
            trans_fat=Decimal('0'),
        )

    def test_add_item_populates_extended_nutrients(self):
        response = self.client.post('/api/plan/add-item/', {
            'date': '2026-03-03',
            'menu_item_id': self.menu_item.id,
            'meal_type': 'lunch',
            'servings': 1,
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(float(response.data['total_fiber']), 5.0)
        self.assertEqual(float(response.data['total_sodium']), 800.0)
        self.assertEqual(float(response.data['total_sugar']), 6.0)
        self.assertEqual(float(response.data['total_cholesterol']), 70.0)
        self.assertEqual(float(response.data['total_saturated_fat']), 8.0)
        self.assertEqual(float(response.data['total_trans_fat']), 0.0)

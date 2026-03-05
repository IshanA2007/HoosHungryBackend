from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from datetime import timedelta
from decimal import Decimal

class Plan(models.Model):
    """Weekly meal plan container"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meal_plans')
    name = models.CharField(max_length=200, default="My Meal Plan")
    description = models.TextField(blank=True)
    
    # Week identification - stores the Sunday of each week
    week_start_date = models.DateField()  # Always a Sunday
    
    # Nutritional goals
    daily_calorie_goal = models.IntegerField(null=True, blank=True)
    daily_protein_goal = models.IntegerField(null=True, blank=True)
    daily_carbs_goal = models.IntegerField(null=True, blank=True)
    daily_fat_goal = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'week_start_date']
        ordering = ['-week_start_date']
    
    def __str__(self):
        return f"{self.user.username}'s plan for week of {self.week_start_date}"
    
    @classmethod
    def get_or_create_for_week(cls, user, date):
        """
        Get or create a plan for the week containing the given date.
        Weeks start on Sunday.
        Returns the Plan instance for that week.
        """
        # Calculate the Sunday of the week containing this date
        # weekday(): Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
        # We want to go back to the most recent Sunday (or stay on Sunday if it's Sunday)
        days_since_sunday = (date.weekday() + 1) % 7
        sunday = date - timedelta(days=days_since_sunday)
        
        # Get user profile defaults if available
        default_cals = None
        default_protein = None
        default_carbs = None
        default_fat = None
        
        if hasattr(user, 'profile'):
            default_cals = user.profile.default_calorie_goal
            default_protein = user.profile.default_protein_goal
            default_carbs = user.profile.default_carbs_goal
            default_fat = user.profile.default_fat_goal
        
        plan, created = cls.objects.get_or_create(
            user=user,
            week_start_date=sunday,
            defaults={
                'name': f"Week of {sunday.strftime('%B %d, %Y')}",
                'daily_calorie_goal': default_cals,
                'daily_protein_goal': default_protein,
                'daily_carbs_goal': default_carbs,
                'daily_fat_goal': default_fat,
            }
        )
        return plan
    
    def get_or_create_daily_plan(self, date):
        """Get or create a DailyMealPlan for a specific date within this week"""
        daily_plan, created = self.daily_plans.get_or_create(
            date=date,
            defaults={
                'total_calories': 0,
                'total_protein': Decimal('0.00'),
                'total_carbs': Decimal('0.00'),
                'total_fat': Decimal('0.00'),
            }
        )
        return daily_plan
    
    def get_week_summary(self):
        """Get summary data for all 7 days of the week"""
        week_data = []
        for i in range(7):
            date = self.week_start_date + timedelta(days=i)
            try:
                daily_plan = self.daily_plans.get(date=date)
                week_data.append({
                    'date': date,
                    'has_meals': daily_plan.meal_items.exists(),
                    'total_calories': daily_plan.total_calories,
                    'meal_count': daily_plan.meal_items.count(),
                    'breakfast_count': daily_plan.meal_items.filter(meal_type='breakfast').count(),
                    'lunch_count': daily_plan.meal_items.filter(meal_type='lunch').count(),
                    'dinner_count': daily_plan.meal_items.filter(meal_type='dinner').count(),
                })
            except DailyMealPlan.DoesNotExist:
                week_data.append({
                    'date': date,
                    'has_meals': False,
                    'total_calories': 0,
                    'meal_count': 0,
                    'breakfast_count': 0,
                    'lunch_count': 0,
                    'dinner_count': 0,
                })
        return week_data


class DailyMealPlan(models.Model):
    """Represents a single day's meals within a weekly plan"""
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='daily_plans')
    date = models.DateField()
    
    # Daily totals (computed from meal items)
    total_calories = models.IntegerField(default=0)
    total_protein = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    total_carbs = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    total_fat = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    total_fiber = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('0.00'))
    total_sodium = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    total_sugar = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('0.00'))
    total_cholesterol = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('0.00'))
    total_saturated_fat = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    total_trans_fat = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        unique_together = ['plan', 'date']
        ordering = ['date']
    
    def __str__(self):
        return f"{self.plan.user.username} - {self.date}"
    
    def calculate_totals(self):
        """Recalculate nutritional totals from all meal items"""
        items = self.meal_items.all()
        self.total_calories = sum(item.total_calories for item in items)
        self.total_protein = sum(item.total_protein for item in items)
        self.total_carbs = sum(item.total_carbs for item in items)
        self.total_fat = sum(item.total_fat for item in items)
        self.total_fiber = sum(item.total_fiber for item in items)
        self.total_sodium = sum(item.total_sodium for item in items)
        self.total_sugar = sum(item.total_sugar for item in items)
        self.total_cholesterol = sum(item.total_cholesterol for item in items)
        self.total_saturated_fat = sum(item.total_saturated_fat for item in items)
        self.total_trans_fat = sum(item.total_trans_fat for item in items)
        self.save()
    
    def get_meals_by_type(self):
        """Return meals organized by meal type"""
        return {
            'breakfast': list(self.meal_items.filter(meal_type='breakfast')),
            'lunch': list(self.meal_items.filter(meal_type='lunch')),
            'dinner': list(self.meal_items.filter(meal_type='dinner')),
            'snack': list(self.meal_items.filter(meal_type='snack')),
        }


class MealItem(models.Model):
    """Individual food item added to a daily meal plan"""
    
    MEAL_TYPE_CHOICES = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snack', 'Snack'),
    ]
    
    daily_plan = models.ForeignKey(DailyMealPlan, on_delete=models.CASCADE, related_name='meal_items')
    meal_type = models.CharField(max_length=10, choices=MEAL_TYPE_CHOICES)
    
    # Reference to menu item (from api app)
    menu_item_id = models.IntegerField()  # References api.MenuItem
    menu_item_name = models.CharField(max_length=200)
    
    # Serving information
    servings = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.25'))]
    )
    
    # Nutritional info per serving (cached from menu item)
    calories_per_serving = models.IntegerField()
    protein_per_serving = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    carbs_per_serving = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    fat_per_serving = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    # Extended nutrition (per serving, cached from NutritionInfo)
    fiber_per_serving = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    sodium_per_serving = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    sugar_per_serving = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    cholesterol_per_serving = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    saturated_fat_per_serving = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    trans_fat_per_serving = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Computed totals based on servings
    total_calories = models.IntegerField()
    total_protein = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    total_carbs = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    total_fat = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    # Extended nutrition totals (computed from per-serving × servings)
    total_fiber = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    total_sodium = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('0.00'))
    total_sugar = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    total_cholesterol = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal('0.00'))
    total_saturated_fat = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    total_trans_fat = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    
    # Metadata
    dining_hall = models.CharField(max_length=50, blank=True)  # ohill, newcomb, runk
    station_name = models.CharField(max_length=200, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['meal_type', 'added_at']
    
    def save(self, *args, **kwargs):
        # Calculate totals before saving
        self.total_calories = int(self.calories_per_serving * float(self.servings))
        self.total_protein = (self.protein_per_serving or Decimal('0')) * self.servings
        self.total_carbs = (self.carbs_per_serving or Decimal('0')) * self.servings
        self.total_fat = (self.fat_per_serving or Decimal('0')) * self.servings
        self.total_fiber = (self.fiber_per_serving or Decimal('0')) * self.servings
        self.total_sodium = (self.sodium_per_serving or Decimal('0')) * self.servings
        self.total_sugar = (self.sugar_per_serving or Decimal('0')) * self.servings
        self.total_cholesterol = (self.cholesterol_per_serving or Decimal('0')) * self.servings
        self.total_saturated_fat = (self.saturated_fat_per_serving or Decimal('0')) * self.servings
        self.total_trans_fat = (self.trans_fat_per_serving or Decimal('0')) * self.servings

        super().save(*args, **kwargs)
        
        # Update daily plan totals
        self.daily_plan.calculate_totals()
    
    def delete(self, *args, **kwargs):
        daily_plan = self.daily_plan
        super().delete(*args, **kwargs)
        daily_plan.calculate_totals()
    
    def __str__(self):
        return f"{self.menu_item_name} ({self.servings} servings) - {self.meal_type}"
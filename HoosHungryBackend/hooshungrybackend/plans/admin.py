from django.contrib import admin
from .models import Plan, DailyMealPlan, MealItem

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['user', 'week_start_date', 'daily_calorie_goal', 'created_at']
    list_filter = ['week_start_date', 'created_at']
    search_fields = ['user__username', 'name']

@admin.register(DailyMealPlan)
class DailyMealPlanAdmin(admin.ModelAdmin):
    list_display = ['plan', 'date', 'total_calories', 'total_protein']
    list_filter = ['date']
    search_fields = ['plan__user__username']

@admin.register(MealItem)
class MealItemAdmin(admin.ModelAdmin):
    list_display = ['menu_item_name', 'meal_type', 'servings', 'total_calories', 'daily_plan']
    list_filter = ['meal_type', 'dining_hall']
    search_fields = ['menu_item_name', 'daily_plan__plan__user__username']
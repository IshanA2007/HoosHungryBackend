from rest_framework import serializers
from .models import Plan, DailyMealPlan, MealItem

class MealItemSerializer(serializers.ModelSerializer):
    servings = serializers.FloatField()  # Explicitly return as float
    total_protein = serializers.FloatField()
    total_carbs = serializers.FloatField()
    total_fat = serializers.FloatField()
    protein_per_serving = serializers.FloatField(allow_null=True)
    carbs_per_serving = serializers.FloatField(allow_null=True)
    fat_per_serving = serializers.FloatField(allow_null=True)
    
    class Meta:
        model = MealItem
        fields = [
            'id', 'menu_item_id', 'menu_item_name', 'meal_type',
            'servings', 'calories_per_serving', 'protein_per_serving',
            'carbs_per_serving', 'fat_per_serving', 'total_calories',
            'total_protein', 'total_carbs', 'total_fat',
            'dining_hall', 'station_name', 'added_at'
        ]
        read_only_fields = ['total_calories', 'total_protein', 'total_carbs', 'total_fat', 'added_at']

class MealItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating meal items from menu items"""
    class Meta:
        model = MealItem
        fields = ['meal_type', 'servings']
    
    def create(self, validated_data):
        # The view will populate menu item data from api.MenuItem
        return super().create(validated_data)

class DailyMealPlanSerializer(serializers.ModelSerializer):
    meals = serializers.SerializerMethodField()
    total_protein = serializers.FloatField()
    total_carbs = serializers.FloatField()
    total_fat = serializers.FloatField()
    
    class Meta:
        model = DailyMealPlan
        fields = [
            'id', 'date', 'total_calories', 'total_protein',
            'total_carbs', 'total_fat', 'meals'
        ]
    
    def get_meals(self, obj):
        meals_by_type = obj.get_meals_by_type()
        return {
            'breakfast': MealItemSerializer(meals_by_type['breakfast'], many=True).data,
            'lunch': MealItemSerializer(meals_by_type['lunch'], many=True).data,
            'dinner': MealItemSerializer(meals_by_type['dinner'], many=True).data,
            'snack': MealItemSerializer(meals_by_type['snack'], many=True).data,
        }

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            'id', 'name', 'description', 'week_start_date',
            'daily_calorie_goal', 'daily_protein_goal',
            'daily_carbs_goal', 'daily_fat_goal',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
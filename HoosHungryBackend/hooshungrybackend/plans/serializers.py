from rest_framework import serializers
from .models import Plan, DailyMealPlan, MealItem

class MealItemSerializer(serializers.ModelSerializer):
    servings = serializers.FloatField()
    total_protein = serializers.FloatField()
    total_carbs = serializers.FloatField()
    total_fat = serializers.FloatField()
    total_fiber = serializers.FloatField()
    total_sodium = serializers.FloatField()
    total_sugar = serializers.FloatField()
    total_cholesterol = serializers.FloatField()
    total_saturated_fat = serializers.FloatField()
    total_trans_fat = serializers.FloatField()
    protein_per_serving = serializers.FloatField(allow_null=True)
    carbs_per_serving = serializers.FloatField(allow_null=True)
    fat_per_serving = serializers.FloatField(allow_null=True)
    fiber_per_serving = serializers.FloatField(allow_null=True)
    sodium_per_serving = serializers.FloatField(allow_null=True)
    sugar_per_serving = serializers.FloatField(allow_null=True)
    cholesterol_per_serving = serializers.FloatField(allow_null=True)
    saturated_fat_per_serving = serializers.FloatField(allow_null=True)
    trans_fat_per_serving = serializers.FloatField(allow_null=True)

    class Meta:
        model = MealItem
        fields = [
            'id', 'menu_item_id', 'menu_item_name', 'meal_type',
            'servings', 'calories_per_serving',
            'protein_per_serving', 'carbs_per_serving', 'fat_per_serving',
            'fiber_per_serving', 'sodium_per_serving', 'sugar_per_serving',
            'cholesterol_per_serving', 'saturated_fat_per_serving', 'trans_fat_per_serving',
            'total_calories', 'total_protein', 'total_carbs', 'total_fat',
            'total_fiber', 'total_sodium', 'total_sugar',
            'total_cholesterol', 'total_saturated_fat', 'total_trans_fat',
            'dining_hall', 'station_name', 'added_at'
        ]
        read_only_fields = [
            'total_calories', 'total_protein', 'total_carbs', 'total_fat',
            'total_fiber', 'total_sodium', 'total_sugar',
            'total_cholesterol', 'total_saturated_fat', 'total_trans_fat',
            'added_at'
        ]

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
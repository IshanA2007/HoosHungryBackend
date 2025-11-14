from rest_framework import serializers
from .models import MenuItem, Station, Period, Day, DiningHall, Allergen, NutritionInfo

class AllergenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Allergen
        fields = ['name']

class NutritionInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = NutritionInfo
        fields = [
            'calories', 'protein', 'total_carbohydrates', 'cholesterol',
            'total_fat', 'trans_fat', 'saturated_fat', 'total_sugars',
            'dietary_fiber', 'sodium', 'serving_size'
        ]

class MenuItemSerializer(serializers.ModelSerializer):
    allergens = AllergenSerializer(many=True, read_only=True)
    nutrition_info = NutritionInfoSerializer(read_only=True)
    
    class Meta:
        model = MenuItem
        fields = [
            'id', 'item_name', 'item_description', 'ingredients',
            'item_category', 'is_gluten', 'is_vegan', 'is_vegetarian',
            'allergens', 'nutrition_info'
        ]

class StationSerializer(serializers.ModelSerializer):
    menu_items = MenuItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Station
        fields = ['id', 'name', 'number', 'menu_items']

class PeriodSerializer(serializers.ModelSerializer):
    stations = StationSerializer(many=True, read_only=True)
    
    class Meta:
        model = Period
        fields = ['id', 'name', 'vendor_id', 'start_time', 'end_time', 'stations']
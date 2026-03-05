from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from django.shortcuts import get_object_or_404
from decimal import Decimal, InvalidOperation

from .models import Plan, DailyMealPlan, MealItem
from .serializers import (
    PlanSerializer, DailyMealPlanSerializer, 
    MealItemSerializer, MealItemCreateSerializer
)
from api.models import MenuItem as APIMenuItem

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_week_plan(request):
    """
    Get or create a plan for a specific week.
    Query params: date (YYYY-MM-DD) - any date in the desired week
    """
    date_str = request.GET.get('date')
    if date_str:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        date = datetime.now().date()
    
    # Get or create the plan for this week
    plan = Plan.get_or_create_for_week(request.user, date)
    
    # Get summary for the entire week
    week_summary = plan.get_week_summary()
    
    return Response({
        'plan_id': plan.id,
        'week_start_date': plan.week_start_date,
        'daily_calorie_goal': plan.daily_calorie_goal,
        'daily_protein_goal': plan.daily_protein_goal,
        'daily_carbs_goal': plan.daily_carbs_goal,
        'daily_fat_goal': plan.daily_fat_goal,
        'week_summary': week_summary,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_daily_plan(request):
    """
    Get detailed meal plan for a specific day.
    Query params: date (YYYY-MM-DD)
    """
    date_str = request.GET.get('date')
    if not date_str:
        return Response(
            {'error': 'Date parameter required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response(
            {"error": "Invalid date format. Use YYYY-MM-DD"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get or create plan for the week containing this date
    plan = Plan.get_or_create_for_week(request.user, date)
    
    # Get or create the daily plan for this specific date
    daily_plan = plan.get_or_create_daily_plan(date)
    
    # Get meals organized by type
    meals_by_type = daily_plan.get_meals_by_type()
    
    return Response({
        'date': date,
        'total_calories': daily_plan.total_calories,
        'total_protein': float(daily_plan.total_protein),
        'total_carbs': float(daily_plan.total_carbs),
        'total_fat': float(daily_plan.total_fat),
        'total_fiber': float(daily_plan.total_fiber),
        'total_sodium': float(daily_plan.total_sodium),
        'total_sugar': float(daily_plan.total_sugar),
        'total_cholesterol': float(daily_plan.total_cholesterol),
        'total_saturated_fat': float(daily_plan.total_saturated_fat),
        'total_trans_fat': float(daily_plan.total_trans_fat),
        'meals': {
            'breakfast': MealItemSerializer(meals_by_type['breakfast'], many=True).data,
            'lunch': MealItemSerializer(meals_by_type['lunch'], many=True).data,
            'dinner': MealItemSerializer(meals_by_type['dinner'], many=True).data,
            'snack': MealItemSerializer(meals_by_type['snack'], many=True).data,
        },
        'goals': {
            'calories': plan.daily_calorie_goal,
            'protein': plan.daily_protein_goal,
            'carbs': plan.daily_carbs_goal,
            'fat': plan.daily_fat_goal,
            'fiber': None,
            'sodium': None,
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_meal_item(request):
    """
    Add a menu item to a meal plan.
    Body: {
        "date": "YYYY-MM-DD",
        "menu_item_id": 123,
        "meal_type": "breakfast|lunch|dinner|snack",
        "servings": 1.0
    }
    """
    date_str = request.data.get('date')
    menu_item_id = request.data.get('menu_item_id')
    meal_type = request.data.get('meal_type')
    servings = request.data.get('servings', 1.0)
    
    # Validation
    if not all([date_str, menu_item_id, meal_type]):
        return Response(
            {"error": "date, menu_item_id, and meal_type are required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response(
            {"error": "Invalid date format. Use YYYY-MM-DD"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get the menu item from api app
    try:
        api_menu_item = APIMenuItem.objects.select_related(
            'nutrition_info', 'station__period__day__dining_hall'
        ).get(id=menu_item_id)
    except APIMenuItem.DoesNotExist:
        return Response(
            {"error": "Menu item not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get or create plan and daily plan
    plan = Plan.get_or_create_for_week(request.user, date)
    daily_plan = plan.get_or_create_daily_plan(date)
    
    # Extract nutrition info
    nutrition = api_menu_item.nutrition_info if hasattr(api_menu_item, 'nutrition_info') else None
    calories = int(nutrition.calories) if nutrition and nutrition.calories else 0
    protein = nutrition.protein if nutrition else None
    carbs = nutrition.total_carbohydrates if nutrition else None
    fat = nutrition.total_fat if nutrition else None
    
    # Create meal item
    meal_item = MealItem.objects.create(
        daily_plan=daily_plan,
        meal_type=meal_type,
        menu_item_id=menu_item_id,
        menu_item_name=api_menu_item.item_name,
        servings=Decimal(str(servings)),
        calories_per_serving=calories,
        protein_per_serving=protein,
        carbs_per_serving=carbs,
        fat_per_serving=fat,
        dining_hall=api_menu_item.station.period.day.dining_hall.name,
        station_name=api_menu_item.station.name,
    )
    
    serializer = MealItemSerializer(meal_item)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_meal_item(request, item_id):
    """
    Update servings for a meal item.
    Body: { "servings": 1.5 }
    """
    try:
        meal_item = MealItem.objects.select_related('daily_plan__plan').get(
            id=item_id,
            daily_plan__plan__user=request.user
        )
    except MealItem.DoesNotExist:
        return Response(
            {"error": "Meal item not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    servings = request.data.get('servings')
    if servings is not None:
        try:
            # Convert to float first, then to Decimal to handle floating point values
            servings_float = float(servings)
            # Round to 2 decimal places to avoid precision issues
            servings_rounded = round(servings_float, 2)
            meal_item.servings = Decimal(str(servings_rounded))
            meal_item.save()
        except (ValueError, TypeError, InvalidOperation) as e:
            return Response(
                {"error": f"Invalid servings value: {servings}. Must be a number."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    serializer = MealItemSerializer(meal_item)
    return Response(serializer.data)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_meal_item(request, item_id):
    """Delete a meal item from the plan"""
    try:
        meal_item = MealItem.objects.select_related('daily_plan__plan').get(
            id=item_id,
            daily_plan__plan__user=request.user
        )
    except MealItem.DoesNotExist:
        return Response(
            {"error": "Meal item not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    meal_item.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_plan_goals(request):
    """
    Update nutritional goals for a plan.
    Query params: date (YYYY-MM-DD)
    Body: {
        "daily_calorie_goal": 2000,
        "daily_protein_goal": 150,
        "daily_carbs_goal": 250,
        "daily_fat_goal": 65
    }
    """
    date_str = request.GET.get('date')
    if not date_str:
        date = datetime.now().date()
    else:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    plan = Plan.get_or_create_for_week(request.user, date)
    
    # Update goals
    if 'daily_calorie_goal' in request.data:
        plan.daily_calorie_goal = request.data['daily_calorie_goal']
    if 'daily_protein_goal' in request.data:
        plan.daily_protein_goal = request.data['daily_protein_goal']
    if 'daily_carbs_goal' in request.data:
        plan.daily_carbs_goal = request.data['daily_carbs_goal']
    if 'daily_fat_goal' in request.data:
        plan.daily_fat_goal = request.data['daily_fat_goal']
    
    plan.save()
    
    serializer = PlanSerializer(plan)
    return Response(serializer.data)
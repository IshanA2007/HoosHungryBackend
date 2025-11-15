from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from .models import DiningHall, Day, Period
from .serializers import PeriodSerializer
from datetime import date

PERIOD_NAME_MAP = {
    "breakfast": "Breakfast",
    "lunch": "Lunch",
    "dinner": "Dinner",
    "late_night": "Late Night",
    "brunch": "Brunch",
}

HALL_NAME_MAP = {
    "ohill": "ohill",
    "newcomb": "newcomb",
    "runk": "runk",
}

@api_view(["GET"])
def hello_world(request):
    return Response({"message": "Hello from your API!"})

@api_view(["GET"])
def menu_info(request):
    # Get query parameters
    period_param = request.query_params.get('period', '').lower()
    hall_param = request.query_params.get('hall', '').lower()
    
    # Validate parameters
    if not period_param or not hall_param:
        return Response(
            {"error": "Both 'period' and 'hall' parameters are required. Example: /menu_info/?period=breakfast&hall=ohill"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if period_param not in PERIOD_NAME_MAP:
        return Response(
            {"error": f"Invalid period. Must be one of: {', '.join(PERIOD_NAME_MAP.keys())}"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if hall_param not in HALL_NAME_MAP:
        return Response(
            {"error": f"Invalid hall. Must be one of: {', '.join(HALL_NAME_MAP.keys())}"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get the actual names for database query
    period_name = PERIOD_NAME_MAP[period_param]
    hall_name = HALL_NAME_MAP[hall_param]
    
    # Get today's date
    today = date.today()
    
    try:
        # Find the dining hall
        dining_hall = DiningHall.objects.get(name=hall_name)
        
        # Find today's day entry for this hall
        day = Day.objects.filter(
            dining_hall=dining_hall,
            date=today
        ).first()
        
        if not day:
            return Response(
                {"error": f"No menu data available for {hall_name} on {today}. Please run the scraper to populate data."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Find the period for this day (case-insensitive match)
        period = Period.objects.filter(
            day=day,
            name__icontains=period_name
        ).first()
        
        if not period:
            # Show what periods are available
            available_periods = Period.objects.filter(day=day).values_list('name', flat=True)
            return Response(
                {
                    "error": f"No {period_name} menu found for {hall_name} on {today}",
                    "available_periods": list(available_periods)
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Serialize and return the data
        serializer = PeriodSerializer(period)
        
        return Response({
            "dining_hall": hall_name,
            "date": str(today),
            "day_name": day.day_name,
            "hall_hours": {
                "open_time": str(day.open_time),
                "close_time": str(day.close_time)
            },
            "period": serializer.data
        })
        
    except DiningHall.DoesNotExist:
        return Response(
            {"error": f"Dining hall '{hall_name}' not found in database"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": f"An error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .serializers import UserSerializer, PlanSerializer, UserProfileSerializer
from .models import Plan, FavoriteItem

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email', '')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if User.objects.filter(username=username).exists():
        return Response(
            {'error': 'Username already exists'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = User.objects.create_user(
        username=username,
        password=password,
        email=email
    )
    
    # Profile is automatically created by the signal
    
    token, _ = Token.objects.get_or_create(user=user)
    
    serializer = UserSerializer(user)
    
    return Response({
        'token': token.key,
        'user': serializer.data
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(username=username, password=password)
    
    if user is None:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token, _ = Token.objects.get_or_create(user=user)
    
    serializer = UserSerializer(user)
    
    return Response({
        'token': token.key,
        'user': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    request.user.auth_token.delete()
    return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def use_ai_feature(request):
    """Example endpoint that decrements AI usage"""
    profile = request.user.profile
    
    if not profile.has_ai_usage_remaining():
        return Response(
            {'error': 'No AI usage remaining'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    profile.decrement_ai_usage()
    
    # Your AI feature logic here
    
    return Response({
        'success': True,
        'remaining_usages': profile.remaining_ai_usages
    })

# Plan management endpoints
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_plans(request):
    """Get all plans for the current user"""
    plans = request.user.profile.plans.all()
    serializer = PlanSerializer(plans, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_plan(request):
    """Create a new plan for the user"""
    name = request.data.get('name')
    description = request.data.get('description', '')
    
    if not name:
        return Response(
            {'error': 'Plan name is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    plan = Plan.objects.create(
        name=name,
        description=description
    )
    
    # Add plan to user's profile
    request.user.profile.plans.add(plan)
    
    serializer = PlanSerializer(plan)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_plan(request, plan_id):
    """Delete a plan"""
    try:
        plan = request.user.profile.plans.get(id=plan_id)
        plan.delete()
        return Response({'message': 'Plan deleted successfully'}, status=status.HTTP_200_OK)
    except Plan.DoesNotExist:
        return Response(
            {'error': 'Plan not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Update user profile fields"""
    profile = request.user.profile

    updatable = [
        'is_vegan', 'is_vegetarian', 'is_gluten_free',
        'default_calorie_goal', 'default_protein_goal',
        'default_carbs_goal', 'default_fat_goal',
        'default_fiber_goal', 'default_sodium_goal',
        'goal_type', 'activity_level',
    ]
    for field in updatable:
        if field in request.data:
            setattr(profile, field, request.data[field])

    profile.save()
    serializer = UserProfileSerializer(profile)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_favorites(request):
    names = list(request.user.favorites.values_list('item_name', flat=True))
    return Response({'favorites': names})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_favorite(request):
    item_name = request.data.get('item_name', '').strip()
    if not item_name:
        return Response({'error': 'item_name is required'}, status=400)
    FavoriteItem.objects.get_or_create(user=request.user, item_name=item_name)
    return Response({'favorites': list(request.user.favorites.values_list('item_name', flat=True))})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_favorite(request):
    item_name = request.data.get('item_name', '').strip()
    request.user.favorites.filter(item_name=item_name).delete()
    return Response({'favorites': list(request.user.favorites.values_list('item_name', flat=True))})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def suggest_goals(request):
    """
    Suggest daily calorie and macro goals based on goal_type and activity_level.
    Uses a simple base calorie formula with activity multipliers.
    """
    profile = request.user.profile

    # Base calories by activity level
    activity_calories = {
        'sedentary': 1800,
        'light': 2000,
        'moderate': 2200,
        'active': 2500,
        'very_active': 2800,
    }

    # Goal-type calorie adjustment
    goal_adjustments = {
        'maintain': 0,
        'lose': -300,
        'gain': +300,
    }

    base = activity_calories.get(profile.activity_level, 2200)
    adjustment = goal_adjustments.get(profile.goal_type, 0)
    calories = base + adjustment

    # Standard macro splits: protein 25%, carbs 50%, fat 25%
    protein = round((calories * 0.25) / 4)   # 4 kcal/g
    carbs = round((calories * 0.50) / 4)     # 4 kcal/g
    fat = round((calories * 0.25) / 9)       # 9 kcal/g

    return Response({
        'calories': calories,
        'protein': protein,
        'carbs': carbs,
        'fat': fat,
        'fiber': 28,       # Standard recommended daily fiber (g)
        'sodium': 2300,    # FDA recommended daily sodium (mg)
    })
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, Plan

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']

class UserProfileSerializer(serializers.ModelSerializer):
    plans = PlanSerializer(many=True, read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['remaining_ai_usages', 'plans', 'premium_member', 'created_at',
                  'is_vegan', 'is_vegetarian', 'is_gluten_free',
                  'default_calorie_goal', 'default_protein_goal',
                  'default_carbs_goal', 'default_fat_goal',
                  'goal_type', 'activity_level']

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile']
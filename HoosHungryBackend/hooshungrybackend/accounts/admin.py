from django.contrib import admin
from .models import UserProfile, Plan

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'remaining_ai_usages', 'premium_member', 'created_at']
    list_filter = ['premium_member', 'created_at']
    search_fields = ['user__username', 'user__email']

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'updated_at']
    search_fields = ['name', 'description']
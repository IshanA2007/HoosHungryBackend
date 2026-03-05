from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Plan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Add any other fields you need for a Plan
    
    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    remaining_ai_usages = models.IntegerField(default=10)  # Or whatever default you want
    plans = models.ManyToManyField(Plan, related_name='users', blank=True)
    
    # Add any other custom fields
    premium_member = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_vegetarian = models.BooleanField(default=False)
    is_gluten_free = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    default_calorie_goal = models.IntegerField(null=True, blank=True)
    default_protein_goal = models.IntegerField(null=True, blank=True)
    default_carbs_goal = models.IntegerField(null=True, blank=True)
    default_fat_goal = models.IntegerField(null=True, blank=True)

    GOAL_TYPE_CHOICES = [
        ('maintain', 'Maintain Weight'),
        ('lose', 'Lose Weight'),
        ('gain', 'Gain Muscle'),
    ]
    ACTIVITY_LEVEL_CHOICES = [
        ('sedentary', 'Sedentary'),
        ('light', 'Lightly Active'),
        ('moderate', 'Moderately Active'),
        ('active', 'Very Active'),
        ('very_active', 'Extremely Active'),
    ]

    goal_type = models.CharField(max_length=20, choices=GOAL_TYPE_CHOICES, default='maintain')
    activity_level = models.CharField(max_length=20, choices=ACTIVITY_LEVEL_CHOICES, default='moderate')

    def __str__(self):
        return f"{self.user.username}'s profile"
    
    def decrement_ai_usage(self):
        """Helper method to decrement AI usage"""
        if self.remaining_ai_usages > 0:
            self.remaining_ai_usages -= 1
            self.save()
            return True
        return False
    
    def has_ai_usage_remaining(self):
        """Check if user has AI usage remaining"""
        return self.remaining_ai_usages > 0

# Automatically create/update profile when user is created/updated
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
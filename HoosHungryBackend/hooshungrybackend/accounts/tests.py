from django.test import TestCase
from django.contrib.auth.models import User
from .models import UserProfile
from accounts.models import UserProfile

class UserProfileDietaryPrefsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')

    def test_dietary_pref_fields_exist_with_defaults(self):
        profile = self.user.profile
        self.assertFalse(profile.is_vegan)
        self.assertFalse(profile.is_vegetarian)
        self.assertFalse(profile.is_gluten_free)

    def test_dietary_prefs_can_be_set(self):
        profile = self.user.profile
        profile.is_vegan = True
        profile.save()
        profile.refresh_from_db()
        self.assertTrue(profile.is_vegan)

class UserProfileGoalFieldsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='goaluser', password='pass')

    def test_profile_has_goal_type_and_activity_level(self):
        profile = self.user.profile
        profile.goal_type = 'lose'
        profile.activity_level = 'moderate'
        profile.save()
        profile.refresh_from_db()
        self.assertEqual(profile.goal_type, 'lose')
        self.assertEqual(profile.activity_level, 'moderate')

    def test_goal_type_defaults_to_maintain(self):
        profile = self.user.profile
        self.assertEqual(profile.goal_type, 'maintain')

    def test_activity_level_defaults_to_moderate(self):
        profile = self.user.profile
        self.assertEqual(profile.activity_level, 'moderate')

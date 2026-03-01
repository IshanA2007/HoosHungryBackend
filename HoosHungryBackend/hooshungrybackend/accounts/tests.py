from django.test import TestCase
from django.contrib.auth.models import User
from .models import UserProfile

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

from django.test import TestCase
from django.contrib.auth.models import User
from django.db import IntegrityError
from .models import UserProfile, ItemRating
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

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

class SuggestGoalsEndpointTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='suggestuser', password='pass')
        self.client = APIClient()
        token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_suggest_goals_returns_all_fields(self):
        response = self.client.get('/accounts/profile/goals/suggest/')
        self.assertEqual(response.status_code, 200)
        for field in ['calories', 'protein', 'carbs', 'fat', 'fiber', 'sodium']:
            self.assertIn(field, response.data)
            self.assertGreater(response.data[field], 0)

    def test_suggest_goals_lose_less_than_maintain(self):
        self.user.profile.goal_type = 'maintain'
        self.user.profile.activity_level = 'moderate'
        self.user.profile.save()
        maintain_response = self.client.get('/accounts/profile/goals/suggest/')

        self.user.profile.goal_type = 'lose'
        self.user.profile.save()
        lose_response = self.client.get('/accounts/profile/goals/suggest/')

        self.assertLess(lose_response.data['calories'], maintain_response.data['calories'])

    def test_suggest_goals_requires_auth(self):
        self.client.credentials()
        response = self.client.get('/accounts/profile/goals/suggest/')
        self.assertEqual(response.status_code, 401)


class ItemRatingModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='rater', password='pass')

    def test_can_create_rating(self):
        rating = ItemRating.objects.create(
            user=self.user, item_name='Grilled Chicken', dining_hall='ohill', is_upvote=True
        )
        self.assertEqual(rating.is_upvote, True)
        self.assertEqual(rating.dining_hall, 'ohill')

    def test_unique_together_enforced(self):
        ItemRating.objects.create(
            user=self.user, item_name='Grilled Chicken', dining_hall='ohill', is_upvote=True
        )
        with self.assertRaises(IntegrityError):
            ItemRating.objects.create(
                user=self.user, item_name='Grilled Chicken', dining_hall='ohill', is_upvote=False
            )


class RatingsEndpointTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='voter', password='pass')
        self.other = User.objects.create_user(username='other', password='pass')
        self.client = APIClient()
        token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_get_ratings_requires_auth(self):
        self.client.credentials()
        res = self.client.get('/accounts/ratings/?dining_hall=ohill')
        self.assertEqual(res.status_code, 401)

    def test_get_ratings_invalid_hall(self):
        res = self.client.get('/accounts/ratings/?dining_hall=invalid')
        self.assertEqual(res.status_code, 400)

    def test_get_ratings_empty_hall(self):
        res = self.client.get('/accounts/ratings/?dining_hall=ohill')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['ratings'], {})

    def test_post_vote_creates_rating(self):
        res = self.client.post('/accounts/ratings/', {
            'item_name': 'Grilled Chicken', 'dining_hall': 'ohill', 'is_upvote': True
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['upvotes'], 1)
        self.assertEqual(res.data['downvotes'], 0)
        self.assertEqual(res.data['user_vote'], 'up')

    def test_post_vote_upserts_on_change(self):
        # First vote: upvote
        res1 = self.client.post('/accounts/ratings/', {
            'item_name': 'Grilled Chicken', 'dining_hall': 'ohill', 'is_upvote': True
        }, format='json')
        self.assertEqual(res1.status_code, 200)
        # Change to downvote
        res = self.client.post('/accounts/ratings/', {
            'item_name': 'Grilled Chicken', 'dining_hall': 'ohill', 'is_upvote': False
        }, format='json')
        self.assertEqual(res.data['upvotes'], 0)
        self.assertEqual(res.data['downvotes'], 1)
        self.assertEqual(res.data['user_vote'], 'down')
        # Only one rating row should exist
        self.assertEqual(ItemRating.objects.filter(user=self.user).count(), 1)

    def test_delete_removes_vote(self):
        self.client.post('/accounts/ratings/', {
            'item_name': 'Grilled Chicken', 'dining_hall': 'ohill', 'is_upvote': True
        }, format='json')
        res = self.client.delete('/accounts/ratings/', {
            'item_name': 'Grilled Chicken', 'dining_hall': 'ohill'
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['upvotes'], 0)
        self.assertEqual(res.data['user_vote'], None)

    def test_get_bulk_returns_rated_items(self):
        # Two users vote on same item
        other_token, _ = Token.objects.get_or_create(user=self.other)
        other_client = APIClient()
        other_client.credentials(HTTP_AUTHORIZATION=f'Token {other_token.key}')

        self.client.post('/accounts/ratings/', {
            'item_name': 'Grilled Chicken', 'dining_hall': 'ohill', 'is_upvote': True
        }, format='json')
        other_client.post('/accounts/ratings/', {
            'item_name': 'Grilled Chicken', 'dining_hall': 'ohill', 'is_upvote': False
        }, format='json')

        res = self.client.get('/accounts/ratings/?dining_hall=ohill')
        self.assertIn('Grilled Chicken', res.data['ratings'])
        self.assertEqual(res.data['ratings']['Grilled Chicken']['upvotes'], 1)
        self.assertEqual(res.data['ratings']['Grilled Chicken']['downvotes'], 1)
        self.assertEqual(res.data['ratings']['Grilled Chicken']['user_vote'], 'up')

    def test_ratings_scoped_to_hall(self):
        # Vote at ohill
        self.client.post('/accounts/ratings/', {
            'item_name': 'Grilled Chicken', 'dining_hall': 'ohill', 'is_upvote': True
        }, format='json')
        # Bulk GET for newcomb should not include the ohill vote
        res = self.client.get('/accounts/ratings/?dining_hall=newcomb')
        self.assertEqual(res.data['ratings'], {})
